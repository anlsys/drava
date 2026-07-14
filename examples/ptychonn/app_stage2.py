import traceback

import drava
import numpy as np

from pipeline_schema import decode_stage1_prediction


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
        self.amp_pred_all: np.ndarray | None = None
        self.phi_pred_all: np.ndarray | None = None
        self.received_mask: np.ndarray | None = None
        self.max_index = 0

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

    def consume(self, frames, base_index) -> None:
        """Accumulate incoming prediction slices. The runtime signals the end of
        the stream via finalize(), so no per-frame completion gating is needed."""
        for payload in frames:
            item = decode_stage1_prediction(payload)
            job_id = item["job_id"]
            start = item["start"]
            end = item["end"]

            if self.current_job_id != job_id:
                self.current_job_id = job_id
                drava.log(drava.DRAVA_VERBOSE_INFO, f"[stage2] job_id={job_id}")

            self._ensure_capacity(end)
            assert self.amp_pred_all is not None
            assert self.phi_pred_all is not None
            assert self.received_mask is not None

            self.amp_pred_all[start:end] = item["pred_amp"]
            self.phi_pred_all[start:end] = item["pred_phi"]
            self.received_mask[start:end] = True
            self.max_index = max(self.max_index, end)

    def finalize(self, expected_frames: int) -> None:
        """Runtime end-of-stream hook: stitch the full reconstruction."""
        n = int(expected_frames) if expected_frames else self.max_index
        if n <= 0 or self.amp_pred_all is None:
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] no frames to stitch")
            return

        side_floor = int(np.floor(np.sqrt(n)))
        stitch_side = side_floor
        used = stitch_side * stitch_side
        if used != n:
            drava.log(
                drava.DRAVA_VERBOSE_WARN,
                f"[stage2-final] expected_frames={n} is not a perfect square; "
                f"using first {used} frames ({stitch_side}x{stitch_side}), dropped={n - used}",
            )
        if used <= 0:
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] not enough frames to stitch")
            return

        stitched_amp = stitch_component(self.amp_pred_all[:used], tst_side=stitch_side)
        stitched_phi = stitch_component(self.phi_pred_all[:used], tst_side=stitch_side)
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"[stage2-final] frames={n} stitched_frames={used} "
            f"stitch_side={stitch_side} "
            f"amp_shape={stitched_amp.shape} phi_shape={stitched_phi.shape}",
        )


_acc = Stage2Accumulator()


def func(frames, base_index) -> None:
    try:
        _acc.consume(frames, base_index)
    except Exception as exc:
        drava.log(drava.DRAVA_VERBOSE_ERROR, f"[stage2] callback exception: {exc}")
        drava.log(drava.DRAVA_VERBOSE_ERROR, traceback.format_exc())
        raise


drava.run(func, on_end_of_stream=_acc.finalize)
