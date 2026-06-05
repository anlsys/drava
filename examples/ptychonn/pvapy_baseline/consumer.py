#!/usr/bin/env python3
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

from pipeline_schema import encode_stage1_prediction
from pva_records import (
    FRAME_BYTES,
    FRAME_CHANNEL,
    OUTPUT_CHANNEL,
    PATCH_SIDE,
    make_eos_prediction_object,
    make_initial_prediction_object,
    make_prediction_object,
    payload_bytes_from_pv,
    pv_field,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume PVA frames and run the same PtychoNN model used by the Drava example."
    )
    parser.add_argument("--input-channel", default=FRAME_CHANNEL)
    parser.add_argument("--output-channel", default=OUTPUT_CHANNEL)
    parser.add_argument("--data-dir", default=os.getenv("PTYCHONN_DATA_DIR", "../PtychoNN_data_partial"))
    parser.add_argument("--infer-batch", type=int, default=int(os.getenv("PVAPY_INFER_BATCH", "128")))
    parser.add_argument("--publish-chunk", type=int, default=16)
    parser.add_argument("--job-id", type=int, default=1)
    parser.add_argument("--monitor-queue", type=int, default=int(os.getenv("PVAPY_MONITOR_QUEUE", "0")))
    parser.add_argument("--warmup-runs", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=0.0, help="0 means wait forever.")
    parser.add_argument("--no-publish-output", dest="publish_output", action="store_false")
    parser.set_defaults(publish_output=True)
    return parser.parse_args()


def configure_gpu_memory_growth(tf_module) -> None:
    gpus = tf_module.config.experimental.list_physical_devices("GPU")
    print(f"[pvapy-consumer] Visible GPUs: {len(gpus)}, {gpus}", flush=True)
    if not gpus:
        return
    try:
        for gpu in gpus:
            tf_module.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as exc:
        print(f"[pvapy-consumer] GPU memory growth configuration failed: {exc}", flush=True)


def load_model(data_dir: Path):
    import tensorflow as tf
    from keras.models import load_model as keras_load_model

    configure_gpu_memory_growth(tf)
    min_epoch = int(np.load(data_dir / "wts4" / "min_epoch.npy"))
    model_path = data_dir / "wts4" / f"weights.{min_epoch:02d}.hdf5"
    model = keras_load_model(model_path)
    print(f"[pvapy-consumer] Loaded model: {model_path}", flush=True)
    return model


class PtychoNNPvaConsumer:
    def __init__(self, args: argparse.Namespace, pvaccess_module, model) -> None:
        self.args = args
        self.pvaccess = pvaccess_module
        self.model = model
        self.done = threading.Event()
        self.lock = threading.Lock()
        self.pending: list[bytes] = []
        self.next_start = 0
        self.expected_frames: int | None = None
        self.last_unique_id = -1
        self.rx_items = 0
        self.rx_bytes = 0
        self.missed_frames = 0
        self.callback_batches = 0
        self.callback_total_s = 0.0
        self.infer_total_s = 0.0
        self.publish_total_s = 0.0
        self.output_msgs = 0
        self.output_unique_id = 0
        self.t0: float | None = None
        self.t_final: float | None = None

        self.output_server = None
        if args.publish_output:
            output_pv = make_initial_prediction_object(self.pvaccess)
            self.output_server = self.pvaccess.PvaServer(args.output_channel, output_pv)
            print(f"[pvapy-consumer] PVA output channel ready: {args.output_channel}", flush=True)

    def warmup(self, runs: int) -> None:
        if runs <= 0:
            return
        dummy = np.zeros((self.args.infer_batch, PATCH_SIDE, PATCH_SIDE, 1), dtype=np.float32)
        for _ in range(runs):
            self.model.predict(dummy, verbose=0)
        print(f"[pvapy-consumer] Warmup done: runs={runs}, batch={self.args.infer_batch}", flush=True)

    def on_update(self, pv_object) -> None:
        start_s = time.perf_counter()
        try:
            self._on_update_inner(pv_object)
        except Exception as exc:
            print(f"[pvapy-consumer] callback exception: {exc}", flush=True)
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
                self.missed_frames += unique_id - self.last_unique_id - 1
            self.last_unique_id = unique_id

        n_total = int(pv_field(pv_object, "nTotal"))
        is_eos = bool(pv_field(pv_object, "eos"))
        if n_total > 0 and (self.expected_frames is None or n_total > self.expected_frames):
            self.expected_frames = n_total

        if is_eos:
            self.flush_pending()
            if self.expected_frames is not None:
                self.missed_frames = max(self.missed_frames, self.expected_frames - self.rx_items)
            self.publish_eos()
            self.t_final = time.perf_counter()
            self.done.set()
            return

        payload = payload_bytes_from_pv(pv_object)
        if len(payload) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(payload)} bytes, expected {FRAME_BYTES}")

        self.rx_items += 1
        self.rx_bytes += len(payload)
        self.pending.append(payload)
        if len(self.pending) >= self.args.infer_batch:
            self.flush_pending()

    def flush_pending(self) -> None:
        if not self.pending:
            return
        batch = self.pending
        self.pending = []
        self.process_batch(batch)

    def process_batch(self, batch: list[bytes]) -> None:
        callback_batch_size = len(batch)
        start = self.next_start
        end = start + callback_batch_size
        self.next_start = end
        self.callback_batches += 1

        tensor = np.frombuffer(b"".join(batch), dtype=np.float32).reshape(
            (callback_batch_size, PATCH_SIDE, PATCH_SIDE, 1),
            order="C",
        )
        infer_t0 = time.perf_counter()
        pred_amp, pred_phi = self.model.predict(tensor, verbose=0)
        self.infer_total_s += time.perf_counter() - infer_t0

        if self.output_server is None:
            return

        pred_amp_3d = pred_amp[..., 0]
        pred_phi_3d = pred_phi[..., 0]
        n_total = self.expected_frames or 0
        publish_t0 = time.perf_counter()
        for off in range(0, callback_batch_size, self.args.publish_chunk):
            chunk_end = min(off + self.args.publish_chunk, callback_batch_size)
            payload = encode_stage1_prediction(
                job_id=self.args.job_id,
                start=start + off,
                end=start + chunk_end,
                n_total=n_total,
                pred_amp=pred_amp_3d[off:chunk_end],
                pred_phi=pred_phi_3d[off:chunk_end],
            )
            pv = make_prediction_object(
                self.pvaccess,
                unique_id=self.output_unique_id,
                job_id=self.args.job_id,
                start=start + off,
                end=start + chunk_end,
                n_total=n_total,
                payload=payload,
            )
            self.output_server.update(pv)
            self.output_unique_id += 1
            self.output_msgs += 1
        self.publish_total_s += time.perf_counter() - publish_t0

    def publish_eos(self) -> None:
        if self.output_server is None:
            return
        n_total = self.expected_frames or self.rx_items
        publish_t0 = time.perf_counter()
        self.output_server.update(make_eos_prediction_object(self.pvaccess, self.output_unique_id, n_total))
        self.output_unique_id += 1
        self.output_msgs += 1
        self.publish_total_s += time.perf_counter() - publish_t0

    def metrics_line(self) -> str:
        if self.t0 is None:
            total_s = 0.0
        else:
            end = self.t_final or time.perf_counter()
            total_s = max(0.0, end - self.t0)
        fps = self.rx_items / total_s if total_s > 0 else 0.0
        cb_avg_ms = (self.callback_total_s / self.callback_batches * 1000.0) if self.callback_batches else 0.0
        expected = self.expected_frames or 0
        total_missing = max(self.missed_frames, expected - self.rx_items) if expected else self.missed_frames
        return (
            "[pvapy-metrics] "
            f"rx_items={self.rx_items} rx_bytes={self.rx_bytes} "
            f"expected_frames={expected} missed_frames={total_missing} "
            f"output_msgs={self.output_msgs} cb_batches={self.callback_batches} "
            f"cb_avg_ms={cb_avg_ms:.3f} infer_total_s={self.infer_total_s:.6f} "
            f"publish_total_s={self.publish_total_s:.6f} stage_total_s={total_s:.6f} "
            f"stage_total_fps={fps:.2f} publish_output={int(self.output_server is not None)}"
        )

    def stop(self) -> None:
        if self.output_server is not None:
            self.output_server.stop()


def main() -> int:
    args = parse_args()
    if args.infer_batch <= 0:
        raise SystemExit("--infer-batch must be > 0")

    try:
        import pvaccess
    except ImportError as exc:
        raise SystemExit("Missing pvaPy module. Install with `pip install pvapy`.") from exc

    data_dir = Path(args.data_dir).resolve()
    model = load_model(data_dir)
    consumer = PtychoNNPvaConsumer(args, pvaccess, model)
    consumer.warmup(args.warmup_runs)

    channel = pvaccess.Channel(args.input_channel)
    channel.setMonitorMaxQueueLength(args.monitor_queue)
    channel.subscribe("ptychonn_consumer", consumer.on_update)
    channel.startMonitor("field()")
    print(
        f"[pvapy-consumer] consumer ready: input={args.input_channel} "
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
        try:
            channel.stopMonitor()
        finally:
            consumer.stop()

    print(consumer.metrics_line(), flush=True)
    exit_code = 2 if consumer.expected_frames and consumer.rx_items != consumer.expected_frames else 0

    # Some EPICS/pvaPy builds abort during interpreter shutdown after PVA
    # server/monitor teardown even after all benchmark metrics have been
    # printed. Exit directly so the harness sees the benchmark status instead
    # of a late cleanup signal.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)


if __name__ == "__main__":
    sys.exit(main())
