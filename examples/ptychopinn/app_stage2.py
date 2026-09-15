"""PtychoPINN stage 2: canvas reassembly and FRC evaluation.

Terminal stage. Decodes the complex object patches from stage 1, splats them
onto the global reconstruction canvas with upstream's barycentric accumulator,
and on end-of-stream divides by the accumulated weights, crops, and scores the
result against ``objectGuess`` with the paper's Fourier ring correlation.

Scan positions are looked up by absolute group index from the prep artifact
rather than carried on the wire, mirroring how the PtychoNN example derives
stitch geometry from the runtime-assigned index. Stage 2 has to read that
artifact anyway for the ground truth and the canvas size.

Concurrency: unlike PtychoNN's stage 2, which writes disjoint ``[start:end]``
slices, this stage accumulates into a *shared, overlapping* canvas. That makes
the in-place scatter-add a data race under parallel callbacks, so
``pipeline.yaml`` sets ``callback_serialize: true`` for this stage. Do not
remove that without replacing the accumulator with a per-thread canvas merged
at end-of-stream.
"""
import json
import traceback

import drava
import numpy as np
import torch

from config import (
    FRC_AUC_CUTOFF,
    GROUPS_FILE,
    META_FILE,
    RECON_PATH,
    SAVE_RECON,
)
from pipeline_schema import decode_stage1_patches

if not META_FILE.is_file() or not GROUPS_FILE.is_file():
    raise RuntimeError(
        f"Missing prep artifacts ({META_FILE}, {GROUPS_FILE}).\n"
        "Run prepare_dataset.py before starting the pipeline."
    )

META = json.loads(META_FILE.read_text(encoding="utf-8"))

GROUP_SIZE = int(META["C"])
MIDDLE_TRIM = int(META["middle_trim"])
CANVAS_SIDE = int(META["canvas_side"])
N_GROUPS = int(META["n_groups"])
WINDOW = int(META["window"])

STAGE2_DEVICE = torch.device("cpu")

with np.load(GROUPS_FILE, allow_pickle=False) as _groups:
    # (M, C, 2) absolute scan positions of every group member.
    COORDS_GLOBAL = torch.from_numpy(
        np.ascontiguousarray(_groups["coords_global"], dtype=np.float32)
    )
    # Centre of mass as reconstruct_image_barycentric actually computes it:
    # the mean over coords_global, not the stored bounded-scan mean. See the
    # note in prepare_dataset.py.
    COM = torch.from_numpy(np.ascontiguousarray(_groups["com"], dtype=np.float32))
    OBJECT_GUESS = np.array(_groups["object_guess"])

CANVAS_SHAPE = (CANVAS_SIDE, CANVAS_SIDE)
# Matches reconstruct_image_barycentric: (width // 2, height // 2), x then y.
CANVAS_CENTER = torch.tensor(
    [CANVAS_SHAPE[1] // 2, CANVAS_SHAPE[0] // 2], dtype=torch.float32
)


def _make_accumulator():
    from ptychopinn_torch.reassembly import VectorizedBarycentricAccumulator

    return VectorizedBarycentricAccumulator(CANVAS_SHAPE, STAGE2_DEVICE)


class Stage2Accumulator:
    def __init__(self):
        self.current_job_id: int | None = None
        self.canvas = torch.zeros(CANVAS_SHAPE, dtype=torch.complex64, device=STAGE2_DEVICE)
        self.counts = torch.zeros(CANVAS_SHAPE, dtype=torch.float32, device=STAGE2_DEVICE)
        self.accumulator = _make_accumulator()
        self.groups_seen = 0
        self.max_index = 0

    def consume(self, frames, base_index) -> None:
        """Splat incoming object patches onto the shared canvas."""
        for payload in frames:
            item = decode_stage1_patches(payload)
            job_id = item["job_id"]
            start = item["start"]
            end = item["end"]

            if self.current_job_id != job_id:
                self.current_job_id = job_id
                drava.log(drava.DRAVA_VERBOSE_INFO, f"[stage2] job_id={job_id}")

            if end > N_GROUPS:
                raise ValueError(
                    f"group range [{start},{end}) exceeds prepared group count "
                    f"{N_GROUPS}; prep artifact and publisher are out of sync"
                )

            patches = torch.from_numpy(item["patches"])          # (B, C, M, M)
            b = patches.shape[0]
            patches = patches.reshape(b * GROUP_SIZE, MIDDLE_TRIM, MIDDLE_TRIM)

            coords = COORDS_GLOBAL[start:end].reshape(b * GROUP_SIZE, 2)
            positions = coords - COM.unsqueeze(0) + CANVAS_CENTER.unsqueeze(0)

            self.accumulator.accumulate_batch(
                self.canvas, self.counts, patches, positions, MIDDLE_TRIM
            )
            self.groups_seen += b
            self.max_index = max(self.max_index, end)

    def finalize(self, expected_frames: int) -> None:
        """Runtime end-of-stream hook: normalise, crop, and score."""
        n = int(expected_frames) if expected_frames else self.max_index
        if self.groups_seen <= 0:
            drava.log(drava.DRAVA_VERBOSE_ERROR, "[stage2-final] no groups received")
            return

        recon_full = (self.canvas / self.counts).numpy()
        n_nan = int(np.isnan(recon_full).sum())

        w = WINDOW
        recon = recon_full[w:-w, w:-w]
        gt = self._ground_truth(recon.shape[0], w)

        frc_auc = float("nan")
        try:
            frc_auc = self._frc_auc(gt, recon)
        except Exception as exc:
            drava.log(
                drava.DRAVA_VERBOSE_ERROR,
                f"[stage2-final] FRC failed: {exc}",
            )
            drava.log(drava.DRAVA_VERBOSE_ERROR, traceback.format_exc())

        if SAVE_RECON:
            try:
                RECON_PATH.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    RECON_PATH,
                    reconstruction=recon,
                    ground_truth=gt,
                    frc_auc=np.array(frc_auc),
                )
                drava.log(
                    drava.DRAVA_VERBOSE_INFO, f"[stage2-final] wrote {RECON_PATH}"
                )
            except Exception as exc:
                drava.log(
                    drava.DRAVA_VERBOSE_ERROR,
                    f"[stage2-final] could not save reconstruction: {exc}",
                )

        # Single machine-parseable line, mirroring PtychoNN's [stage2-final].
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"[stage2-final] frames={n} groups={self.groups_seen} "
            f"canvas_side={CANVAS_SIDE} window={w} "
            f"recon_shape={recon.shape[0]}x{recon.shape[1]} "
            f"gt_shape={gt.shape[0]}x{gt.shape[1]} "
            f"nan_px={n_nan} frc_auc={frc_auc:.6f} "
            f"dataset={META['dataset']} model={META['model_key']}",
        )

    @staticmethod
    def _ground_truth(side: int, w: int) -> np.ndarray:
        from ptychopinn_torch.helper import center_crop

        gt = np.squeeze(OBJECT_GUESS)
        gt = gt[w:-w, w:-w]
        return center_crop(gt, side)

    @staticmethod
    def _frc_auc(gt: np.ndarray, recon: np.ndarray) -> float:
        """Paper FRC: phase-ramp match + Tukey taper, then FSC, AUC to cutoff.

        Calls ``frc_preprocess_images`` and ``FSC`` directly rather than
        ``analysis.preprocess_and_calculate_frc``, because that helper is
        defined twice in upstream's analysis.py with two different AUC cutoffs
        (1.0 then 0.5, the second shadowing the first). Being explicit here
        removes the ambiguity about which number is being reported.
        """
        from ptychopinn_torch.eval.eval_metrics import FSC
        from ptychopinn_torch.eval.frc import frc_preprocess_images

        aligned_gt, aligned_pred = frc_preprocess_images(
            gt, recon, image_prop="complex", verbose=False, align=False
        )
        fr_curve, x_fr, _t_curve, _x_t = FSC(aligned_gt, aligned_pred)

        over = np.where(x_fr - FRC_AUC_CUTOFF > 0)[0]
        if len(over) == 0:
            return float(np.mean(fr_curve))
        cut = int(over[0])
        return float(np.sum(fr_curve[:cut]) / cut)


_acc = Stage2Accumulator()
drava.log(
    drava.DRAVA_VERBOSE_INFO,
    f"[stage2] canvas={CANVAS_SIDE}x{CANVAS_SIDE} groups={N_GROUPS} "
    f"C={GROUP_SIZE} middle_trim={MIDDLE_TRIM} window={WINDOW}",
)


def func(frames, base_index) -> None:
    try:
        _acc.consume(frames, base_index)
    except Exception as exc:
        drava.log(drava.DRAVA_VERBOSE_ERROR, f"[stage2] callback exception: {exc}")
        drava.log(drava.DRAVA_VERBOSE_ERROR, traceback.format_exc())
        raise


drava.run(func, on_end_of_stream=_acc.finalize)
