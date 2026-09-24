"""Score the same dataset/model through upstream's own code path.

This is the decisive correctness check for the Drava example. Comparing the
pipeline's FRC directly against the paper conflates two different questions:
"does the Drava pipeline reproduce PtychoPINN?" and "does PtychoPINN on this
machine reproduce the paper?". This script answers the first by running
upstream's ``generate_gt_and_recon`` -- the exact path from
``recreate_results.ipynb`` -- and scoring it with the *same* explicit FRC
computation stage 2 uses.

Expect the two AUC values to agree to roughly 2-3 decimal places. They are not
bit-identical: FP16 autocast makes reductions batch-composition dependent, and
the Drava path batches by callback rather than by DataLoader.

Upstream's analysis.py hardcodes ``tracking_uri = file:$PWD/mlruns`` and takes
dataset paths like ``data/W`` relative to the CWD, so this script chdirs into
the data root before calling it.

Requires a GPU: ``reconstruct_image_barycentric`` calls CUDA unconditionally.

Usage::

    python verify_against_upstream.py
    python verify_against_upstream.py --dataset W --model PS_W
    python verify_against_upstream.py --compare prep/W_PS_W/reconstruction.npz
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path

import numpy as np

import config as cfg


@contextlib.contextmanager
def chdir(path: Path):
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def frc_auc(gt: np.ndarray, recon: np.ndarray, cutoff: float) -> float:
    """Identical to app_stage2.Stage2Accumulator._frc_auc."""
    from ptychopinn_torch.eval.eval_metrics import FSC
    from ptychopinn_torch.eval.frc import frc_preprocess_images

    aligned_gt, aligned_pred = frc_preprocess_images(
        gt, recon, image_prop="complex", verbose=False, align=False
    )
    fr_curve, x_fr, _t, _xt = FSC(aligned_gt, aligned_pred)
    over = np.where(x_fr - cutoff > 0)[0]
    if len(over) == 0:
        return float(np.mean(fr_curve))
    cut = int(over[0])
    return float(np.sum(fr_curve[:cut]) / cut)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", default=cfg.DATASET)
    parser.add_argument("--model", default=cfg.MODEL_KEY)
    parser.add_argument("--data-root", default=str(cfg.DATA_ROOT))
    parser.add_argument("--compare", default=None,
                        help="path to the Drava reconstruction.npz to diff against")
    parser.add_argument("--save", default=None,
                        help="write upstream's recon/gt to this .npz")
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    if not (data_root / "mlruns").is_dir():
        raise SystemExit(f"No mlruns/ under {data_root}. Run download_zenodo.py first.")
    if args.model not in cfg.MODEL_IDS:
        raise SystemExit(
            f"Unknown model key {args.model!r}. Known: {', '.join(sorted(cfg.MODEL_IDS))}"
        )

    print(f"[verify] data_root = {data_root}")
    print(f"[verify] dataset={args.dataset} model={args.model} "
          f"run_id={cfg.MODEL_IDS[args.model]}")
    print("[verify] running upstream generate_gt_and_recon() ...")

    with chdir(data_root):
        from ptychopinn_torch.notebooks.analysis import generate_gt_and_recon

        gt, recon = generate_gt_and_recon(
            f"data/{args.dataset}",
            args.model,
            cfg.MODEL_IDS,
            cfg.WINDOW_SIZES,
        )

    gt = np.asarray(gt)
    recon = np.asarray(recon)
    print(f"[verify] upstream recon={recon.shape} gt={gt.shape}")

    upstream_auc = frc_auc(gt, recon, cfg.FRC_AUC_CUTOFF)
    print(f"\n[verify] upstream FRC AUC (0..{cfg.FRC_AUC_CUTOFF}) = {upstream_auc:.6f}")

    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out, reconstruction=recon, ground_truth=gt,
                            frc_auc=np.array(upstream_auc))
        print(f"[verify] wrote {out}")

    compare_path = Path(args.compare) if args.compare else cfg.RECON_PATH
    if not compare_path.is_file():
        print(f"\n[verify] no Drava reconstruction at {compare_path}; "
              "run the pipeline then re-run with --compare")
        return 0

    with np.load(compare_path) as drava_out:
        drava_recon = np.asarray(drava_out["reconstruction"])
        drava_gt = np.asarray(drava_out["ground_truth"])
        drava_auc = float(np.asarray(drava_out["frc_auc"]))

    print(f"\n[verify] drava    FRC AUC = {drava_auc:.6f}")
    print(f"[verify] upstream FRC AUC = {upstream_auc:.6f}")
    print(f"[verify] absolute difference = {abs(drava_auc - upstream_auc):.6f}")

    print(f"\n[verify] shapes: drava={drava_recon.shape} upstream={recon.shape}")
    if drava_recon.shape != recon.shape:
        print("[verify] SHAPE MISMATCH -- the canvas geometry differs. This is a "
              "real discrepancy, not numerical noise. Check max_offset/com in "
              "prep/meta.json against upstream's 'Canvas size:' line.")
        return 1

    if not np.array_equal(drava_gt, gt):
        print("[verify] WARNING: ground truth differs between the two paths")

    # Complex reconstructions are defined up to a global phase/scale, so compare
    # after the same least-squares complex alignment the FRC preprocessing uses.
    num = np.nansum(np.real(np.conj(recon) * drava_recon))
    den = np.nansum(np.abs(recon) ** 2)
    scale = num / den if den else 1.0
    resid = drava_recon - scale * recon
    denom = np.sqrt(np.nansum(np.abs(drava_recon) ** 2))
    nrmse = float(np.sqrt(np.nansum(np.abs(resid) ** 2)) / denom) if denom else float("nan")
    print(f"[verify] complex NRMSE (drava vs upstream, scale-aligned) = {nrmse:.6f}")

    verdict = "PASS" if abs(drava_auc - upstream_auc) < 0.01 else "INVESTIGATE"
    print(f"\n[verify] {verdict}: |dAUC| "
          f"{'<' if verdict == 'PASS' else '>='} 0.01")
    print(json.dumps({
        "dataset": args.dataset,
        "model": args.model,
        "drava_frc_auc": drava_auc,
        "upstream_frc_auc": upstream_auc,
        "abs_diff": abs(drava_auc - upstream_auc),
        "complex_nrmse": nrmse,
    }, indent=2))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
