#!/usr/bin/env python3
"""Stage-2 pvaPy consumer for the two-stage PtychoNN baseline.

This mirrors Drava's ``app_stage2.py``: it monitors the stage-1 prediction PVA
channel, decodes ``stage1_prediction_batch`` payloads with the shared
``pipeline_schema``, accumulates amplitude/phase predictions, and performs the
same overlap-add stitching once all frames are received (or on EOS). It keeps
Drava and pvaPy on identical science so the end-to-end comparison isolates the
transport/dispatch path.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PTYCHONN_DIR = HERE.parent
if str(PTYCHONN_DIR) not in sys.path:
    sys.path.insert(0, str(PTYCHONN_DIR))

from pipeline_schema import decode_stage1_prediction
from pva_records import OUTPUT_CHANNEL, pv_field, payload_bytes_from_pv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume stage-1 PVA predictions and run PtychoNN stitching (stage 2)."
    )
    parser.add_argument("--input-channel", default=OUTPUT_CHANNEL)
    parser.add_argument("--monitor-queue", type=int, default=int(os.getenv("PVAPY_MONITOR_QUEUE", "0")))
    parser.add_argument("--timeout-s", type=float, default=0.0, help="0 means wait forever.")
    return parser.parse_args()


def stitch_component(
        pred_patches_2d: np.ndarray,
        tst_side: int = 60,
        patch_size: int = 64,
        point_size: int = 3,
) -> np.ndarray:
    """Overlap-add stitching identical to Drava's app_stage2.stitch_component."""
    overlap = 4 * point_size
    composite = np.zeros((tst_side * point_size + overlap, tst_side * point_size + overlap), float)
    ctr = np.zeros_like(composite)

    data_reshaped = pred_patches_2d.reshape(tst_side, tst_side, patch_size, patch_size)[
        :,
        :,
        patch_size // 2 - overlap // 2: patch_size // 2 + overlap // 2,
        patch_size // 2 - overlap // 2: patch_size // 2 + overlap // 2,
    ]

    for i in range(tst_side):
        for j in range(tst_side):
            r0 = point_size * i
            c0 = point_size * j
            composite[r0: r0 + overlap, c0: c0 + overlap] += data_reshaped[i, j]
            ctr[r0: r0 + overlap, c0: c0 + overlap] += 1

    stitched = (
            composite[overlap // 2: -overlap // 2, overlap // 2: -overlap // 2]
            / ctr[overlap // 2: -overlap // 2, overlap // 2: -overlap // 2]
    )
    return stitched


class Stage2PvaConsumer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.done = threading.Event()
        self.lock = threading.Lock()

        self.current_job_id: int | None = None
        self.expected_frames: int | None = None
        self.amp_pred_all: np.ndarray | None = None
        self.phi_pred_all: np.ndarray | None = None
        self.received_mask: np.ndarray | None = None

        self.total_received = 0
        self.total_unique_received = 0
        self.finalized = False

        # transport/observability counters
        self.rx_msgs = 0
        self.rx_bytes = 0
        self.last_unique_id = -1
        self.missed_msgs = 0
        self.callback_batches = 0
        self.callback_total_s = 0.0
        self.stitch_total_s = 0.0
        self.stitch_side = 0
        self.stitched_frames = 0
        self.t0: float | None = None
        self.t_final: float | None = None

    # -- accumulation (ported from Drava app_stage2.Stage2Accumulator) --------
    def reset_job(self, job_id: int) -> None:
        self.current_job_id = job_id
        self.expected_frames = None
        self.amp_pred_all = None
        self.phi_pred_all = None
        self.received_mask = None
        self.total_received = 0
        self.total_unique_received = 0
        self.finalized = False
        print(f"[pvapy-stage2] reset job_id={job_id}", flush=True)

    def _ensure_capacity(self, n_frames: int) -> None:
        if n_frames <= 0:
            return
        if self.amp_pred_all is None:
            self.amp_pred_all = np.empty((n_frames, 64, 64), dtype=np.float32)
            self.phi_pred_all = np.empty((n_frames, 64, 64), dtype=np.float32)
            self.received_mask = np.zeros((n_frames,), dtype=bool)
            return
        assert self.phi_pred_all is not None
        assert self.received_mask is not None
        cur = self.amp_pred_all.shape[0]
        if n_frames <= cur:
            return
        amp_new = np.empty((n_frames, 64, 64), dtype=np.float32)
        phi_new = np.empty((n_frames, 64, 64), dtype=np.float32)
        mask_new = np.zeros((n_frames,), dtype=bool)
        amp_new[:cur] = self.amp_pred_all
        phi_new[:cur] = self.phi_pred_all
        mask_new[:cur] = self.received_mask
        self.amp_pred_all = amp_new
        self.phi_pred_all = phi_new
        self.received_mask = mask_new

    def on_eos(self, eos_frames: int) -> None:
        if eos_frames <= 0:
            return
        if self.expected_frames is None or eos_frames > self.expected_frames:
            self.expected_frames = eos_frames
            self._ensure_capacity(eos_frames)
            print(f"[pvapy-stage2] EOS received: expected_frames={self.expected_frames}", flush=True)
        self._try_finalize()

    def consume(self, payload: bytes) -> None:
        if self.finalized:
            return
        item = decode_stage1_prediction(payload)
        job_id = item["job_id"]
        start = item["start"]
        end = item["end"]
        n_total = item["n_total"]
        pred_amp = item["pred_amp"]
        pred_phi = item["pred_phi"]

        if self.current_job_id != job_id:
            self.reset_job(job_id)

        if n_total > 0:
            if self.expected_frames is None or n_total > self.expected_frames:
                self.expected_frames = n_total
        self._ensure_capacity(max(end, self.expected_frames or 0))
        assert self.amp_pred_all is not None
        assert self.phi_pred_all is not None
        assert self.received_mask is not None

        self.amp_pred_all[start:end] = pred_amp
        self.phi_pred_all[start:end] = pred_phi
        already = self.received_mask[start:end].copy()
        self.received_mask[start:end] = True
        self.total_unique_received += int((~already).sum())
        self.total_received += (end - start)

        self._try_finalize()

    def _try_finalize(self) -> None:
        if self.finalized:
            return
        if self.expected_frames is None:
            return
        if self.total_unique_received < self.expected_frames:
            return
        self.finalize()

    def finalize(self) -> None:
        assert self.amp_pred_all is not None
        assert self.phi_pred_all is not None
        assert self.expected_frames is not None

        n = self.expected_frames
        if n <= 0:
            print("[pvapy-stage2-final] expected_frames must be > 0", flush=True)
            self.finalized = True
            return

        side_floor = int(np.floor(np.sqrt(n)))
        is_perfect_square = (side_floor * side_floor) == n
        stitch_side = side_floor
        used = stitch_side * stitch_side
        dropped = n - used
        if not is_perfect_square:
            print(
                f"[pvapy-stage2-final] expected_frames={n} is not a perfect square; "
                f"using first {used} frames ({stitch_side}x{stitch_side}), dropped={dropped}",
                flush=True,
            )
        if used <= 0:
            print("[pvapy-stage2-final] not enough frames to stitch", flush=True)
            self.finalized = True
            return

        stitch_t0 = time.perf_counter()
        stitched_amp = stitch_component(self.amp_pred_all[:used], tst_side=stitch_side)
        stitched_phi = stitch_component(self.phi_pred_all[:used], tst_side=stitch_side)
        self.stitch_total_s += time.perf_counter() - stitch_t0

        self.stitch_side = stitch_side
        self.stitched_frames = used
        self.finalized = True
        self.t_final = time.perf_counter()
        print(
            f"[pvapy-stage2-final] frames={self.expected_frames} stitched_frames={used} "
            f"stitch_side={stitch_side} "
            f"amp_shape={stitched_amp.shape} phi_shape={stitched_phi.shape}",
            flush=True,
        )
        self.done.set()

    # -- PVA monitor callback -------------------------------------------------
    def on_update(self, pv_object) -> None:
        start_s = time.perf_counter()
        try:
            self._on_update_inner(pv_object)
        except Exception as exc:
            print(f"[pvapy-stage2] callback exception: {exc}", flush=True)
            self.done.set()
            raise
        finally:
            self.callback_total_s += time.perf_counter() - start_s

    def _on_update_inner(self, pv_object) -> None:
        unique_id = int(pv_field(pv_object, "uniqueId"))
        if unique_id < 0:
            return

        with self.lock:
            if self.t0 is None:
                self.t0 = time.perf_counter()
            if unique_id <= self.last_unique_id:
                return
            if self.last_unique_id >= 0 and unique_id > self.last_unique_id + 1:
                self.missed_msgs += unique_id - self.last_unique_id - 1
            self.last_unique_id = unique_id

        is_eos = bool(pv_field(pv_object, "eos"))
        n_total = int(pv_field(pv_object, "nTotal"))

        if is_eos:
            self.on_eos(n_total)
            if not self.finalized:
                # EOS arrived but not all frames present; finalize best-effort.
                self.t_final = time.perf_counter()
                self.done.set()
            return

        payload = payload_bytes_from_pv(pv_object)
        self.rx_msgs += 1
        self.rx_bytes += len(payload)
        self.callback_batches += 1
        self.consume(payload)

    def metrics_line(self) -> str:
        if self.t0 is None:
            total_s = 0.0
        else:
            end = self.t_final or time.perf_counter()
            total_s = max(0.0, end - self.t0)
        fps = self.stitched_frames / total_s if total_s > 0 else 0.0
        cb_avg_ms = (self.callback_total_s / self.callback_batches * 1000.0) if self.callback_batches else 0.0
        return (
            "[pvapy-stage2-metrics] "
            f"rx_msgs={self.rx_msgs} rx_bytes={self.rx_bytes} "
            f"missed_msgs={self.missed_msgs} cb_batches={self.callback_batches} "
            f"cb_avg_ms={cb_avg_ms:.3f} stitch_total_s={self.stitch_total_s:.6f} "
            f"stage_total_s={total_s:.6f} stage_total_fps={fps:.2f} "
            f"expected_frames={self.expected_frames or 0} "
            f"stitched_frames={self.stitched_frames} stitch_side={self.stitch_side}"
        )


def main() -> int:
    args = parse_args()

    try:
        import pvaccess
    except ImportError as exc:
        raise SystemExit("Missing pvaPy module. Install with `pip install pvapy`.") from exc

    consumer = Stage2PvaConsumer(args)

    channel = pvaccess.Channel(args.input_channel)
    channel.setMonitorMaxQueueLength(args.monitor_queue)
    channel.subscribe("ptychonn_stage2_consumer", consumer.on_update)
    channel.startMonitor("field()")
    print(
        f"[pvapy-stage2] consumer ready: input={args.input_channel} "
        f"monitor_queue={args.monitor_queue}",
        flush=True,
    )

    try:
        if args.timeout_s > 0:
            consumer.done.wait(args.timeout_s)
        else:
            while not consumer.done.wait(0.5):
                pass
    finally:
        channel.stopMonitor()

    print(consumer.metrics_line(), flush=True)
    exit_code = 0 if consumer.finalized else 2

    # Match consumer.py: some pvaPy builds abort during interpreter shutdown
    # after monitor teardown; exit directly so the harness sees the status.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)


if __name__ == "__main__":
    sys.exit(main())
