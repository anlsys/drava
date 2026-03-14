import threading
import traceback

import drava
import numpy as np

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
    def __init__(self):
        self.current_job_id: int | None = None
        self.expected_frames: int | None = None
        self.amp_pred_all: np.ndarray | None = None
        self.phi_pred_all: np.ndarray | None = None
        self.received_mask: np.ndarray | None = None

        self.total_received = 0
        self.total_unique_received = 0
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
        try:
            item = decode_stage1_prediction(payload)
        except Exception as exc:
            drava.log(
                drava.DRAVA_VERBOSE_ERROR,
                f"[stage2] decode failed payload_len={len(payload)} error={exc}",
            )
            raise
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
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] expected_frames must be > 0")
            self.finalized = True
            return

        side_floor = int(np.floor(np.sqrt(n)))
        is_perfect_square = (side_floor * side_floor) == n

        stitch_side = side_floor
        used = stitch_side * stitch_side
        dropped = n - used
        if not is_perfect_square:
            drava.log(
                drava.DRAVA_VERBOSE_WARN,
                f"[stage2-final] expected_frames={n} is not a perfect square; "
                f"using first {used} frames ({stitch_side}x{stitch_side}), dropped={dropped}",
            )
        if used <= 0:
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] not enough frames to stitch")
            self.finalized = True
            return

        stitched_amp = stitch_component(self.amp_pred_all[:used], tst_side=stitch_side)
        stitched_phi = stitch_component(self.phi_pred_all[:used], tst_side=stitch_side)
        stats = drava.stats_snapshot_py()
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"[stage2-final] frames={self.expected_frames} stitched_frames={used} "
            f"stitch_side={stitch_side} amp_shape={stitched_amp.shape} "
            f"phi_shape={stitched_phi.shape}",
        )
        if stats.get("rc", drava.DRAVA_ERROR) == drava.DRAVA_SUCCESS:
            rx_frames = int(stats.get("rx_frames", 0))
            rx_first_ns = int(stats.get("rx_first_ns", 0))
            rx_last_ns = int(stats.get("rx_last_ns", 0))
            rx_fps = (
                (rx_frames * 1.0e9) / (rx_last_ns - rx_first_ns)
                if rx_frames > 0 and rx_last_ns > rx_first_ns
                else 0.0
            )
            stage_samples = int(stats.get("stage_latency_samples", 0))
            stage_ns_sum = int(stats.get("stage_latency_ns_sum", 0))
            stage_avg_ms = (
                (stage_ns_sum / stage_samples) / 1.0e6
                if stage_samples > 0
                else 0.0
            )
            drava.log(
                drava.DRAVA_VERBOSE_INFO,
                f"[stage2-runtime] rx_frames={rx_frames} rx_fps={rx_fps:.2f} "
                f"stage_avg_ms={stage_avg_ms:.3f}",
            )
        self.finalized = True


_acc = Stage2Accumulator()


def func(frames) -> None:
    try:
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
    except Exception as exc:
        drava.log(drava.DRAVA_VERBOSE_ERROR, f"[stage2] callback exception: {exc}")
        drava.log(drava.DRAVA_VERBOSE_ERROR, traceback.format_exc())
        raise


rc = drava.init()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(
        f"drava.init() failed with rc={rc}. "
        "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
    )

try:
    drava.log(drava.DRAVA_VERBOSE_INFO, "[stage2] registering callback")
    drava.register_routine_py(func)
    drava.log(drava.DRAVA_VERBOSE_INFO, "[stage2] entering listen loop")
    rc = drava.listen_py()
    drava.log(drava.DRAVA_VERBOSE_INFO, f"[stage2] listen returned rc={rc}")
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
finally:
    rc = drava.deinit()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.deinit() failed with rc={rc}")
