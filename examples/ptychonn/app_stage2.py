import time
import threading

import drava
import numpy as np

from config import LOG_EVERY, STAGE2_SCAN_SIDE
from pipeline_schema import decode_stage1_prediction

EOS_PREFIX = b"DRAVA_EOS:"


def stitch_component(
        pred_patches_2d: np.ndarray,
        tst_side: int = 60,
        patch_size: int = 64,
        point_size: int = 3,
) -> np.ndarray:
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


class Stage2Accumulator:
    def __init__(self, tst_side: int):
        self.tst_side = tst_side
        self.current_job_id: int | None = None
        self.expected_frames: int | None = None
        self.amp_pred_all: np.ndarray | None = None
        self.phi_pred_all: np.ndarray | None = None
        self.received_mask: np.ndarray | None = None

        self.total_received = 0
        self.total_unique_received = 0
        self.t0: float | None = None
        self.next_log = LOG_EVERY
        self.finalized = False
        self.lock = threading.Lock()

    def reset_job(self, job_id: int) -> None:
        self.current_job_id = job_id
        self.expected_frames = None
        self.amp_pred_all = None
        self.phi_pred_all = None
        self.received_mask = None
        self.total_received = 0
        self.total_unique_received = 0
        self.t0 = None
        self.next_log = LOG_EVERY
        self.finalized = False
        drava.log(drava.DRAVA_VERBOSE_INFO, f"[stage2] reset job_id={job_id}")

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
            drava.log(drava.DRAVA_VERBOSE_INFO, f"[stage2] EOS received: expected_frames={self.expected_frames}")
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

        if self.t0 is None:
            self.t0 = time.perf_counter()

        if n_total > 0:
            if self.expected_frames is None or n_total > self.expected_frames:
                self.expected_frames = n_total
        self._ensure_capacity(max(end, self.expected_frames or 0))
        assert self.amp_pred_all is not None
        assert self.phi_pred_all is not None
        assert self.received_mask is not None

        self.amp_pred_all[start:end] = pred_amp
        self.phi_pred_all[start:end] = pred_phi
        already = self.received_mask[start:end]
        self.received_mask[start:end] = True
        self.total_unique_received += int((~already).sum())
        self.total_received += (end - start)

        got = self.total_unique_received
        total = self.expected_frames if self.expected_frames is not None else self.received_mask.size
        if got >= self.next_log:
            now = time.perf_counter()
            elapsed = now - self.t0
            consume_fps = (got / elapsed) if elapsed > 0 else float("inf")
            drava.log(
                drava.DRAVA_VERBOSE_INFO,
                f"[stage2] received={got}/{total} consume_avg_fps={consume_fps:.2f}",
            )
            self.next_log += LOG_EVERY

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
        assert self.t0 is not None
        assert self.expected_frames is not None

        n = self.expected_frames
        if n <= 0:
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] expected_frames must be > 0")
            self.finalized = True
            return

        if n == (self.tst_side * self.tst_side):
            stitch_side = self.tst_side
            used = n
        else:
            stitch_side = int(np.floor(np.sqrt(n)))
            used = stitch_side * stitch_side
            dropped = n - used
            drava.log(
                drava.DRAVA_VERBOSE_WARN,
                f"[stage2-final] expected_frames={n} is not a perfect square; "
                f"using first {used} frames ({stitch_side}x{stitch_side}), dropped={dropped}",
            )
        if used <= 0:
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] not enough frames to stitch")
            self.finalized = True
            return

        t0 = time.perf_counter()
        stitched_amp = stitch_component(self.amp_pred_all[:used], tst_side=stitch_side)
        stitched_phi = stitch_component(self.phi_pred_all[:used], tst_side=stitch_side)
        t1 = time.perf_counter()

        consume_elapsed = t0 - self.t0
        consume_fps = (
            self.total_unique_received / consume_elapsed
            if consume_elapsed > 0
            else float("inf")
        )
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"[stage2-final] frames={self.expected_frames} stitched_frames={used} "
            f"stitch_side={stitch_side} consume_avg_fps={consume_fps:.2f} "
            f"stitch_time_s={(t1 - t0):.3f} "
            f"amp_shape={stitched_amp.shape} phi_shape={stitched_phi.shape}",
        )
        self.finalized = True


_acc = Stage2Accumulator(tst_side=STAGE2_SCAN_SIDE)


def func(frames) -> None:
    with _acc.lock:
        for raw in frames:
            if raw.startswith(EOS_PREFIX):
                try:
                    eos_frames = int(raw[len(EOS_PREFIX):].decode("ascii"))
                except ValueError:
                    drava.log(drava.DRAVA_VERBOSE_WARN, f"[stage2] Ignoring malformed EOS marker: {raw!r}")
                    continue
                _acc.on_eos(eos_frames)
            else:
                _acc.consume(raw)


rc = drava.init()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(
        f"drava.init() failed with rc={rc}. "
        "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
    )

try:
    drava.register_routine_py(func)
    rc = drava.listen_py()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
finally:
    rc = drava.deinit()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.deinit() failed with rc={rc}")
