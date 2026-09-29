"""Bisection tool: reconstruct offline from the prep artifacts, without Drava.

When the pipeline's FRC disagrees with ``verify_against_upstream.py``, the
cause is in one of two places:

  A. the prep artifacts + this example's reassembly maths, or
  B. the streaming path (chunking, base_index, the wire schema, transport).

This script exercises exactly A and nothing of B: it reads groups.npz and
meta.json, runs ``forward_predict`` on the same groups in the same channel
order, accumulates with the same barycentric call stage 2 uses, and scores the
result with the same FRC.

Interpretation:

  * FRC close to upstream's  -> A is fine, the bug is in the streaming path.
  * FRC close to the pipeline's -> the bug is in prep or the reassembly maths,
    and the transport is exonerated.

Usage::

    python debug_offline_reconstruct.py
    python debug_offline_reconstruct.py --batch-size 512   # match upstream
    python debug_offline_reconstruct.py --no-amp           # test fp16 effects
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import torch

import config as cfg


def frc_auc(gt: np.ndarray, recon: np.ndarray, cutoff: float,
            align: bool = False) -> float:
    """FRC AUC. ``align=True`` enables sub-pixel registration first.

    The published path uses align=False, i.e. it assumes the reconstruction is
    already registered to the ground truth. If align=True scores far higher
    than align=False, the reconstruction is *shifted* rather than degraded,
    which points at the canvas centre-of-mass rather than at the model.
    """
    from ptychopinn_torch.eval.eval_metrics import FSC
    from ptychopinn_torch.eval.frc import frc_preprocess_images

    aligned_gt, aligned_pred = frc_preprocess_images(
        gt, recon, image_prop="complex", verbose=False, align=align
    )
    fr_curve, x_fr, _t, _xt = FSC(aligned_gt, aligned_pred)
    over = np.where(x_fr - cutoff > 0)[0]
    if len(over) == 0:
        return float(np.mean(fr_curve))
    cut = int(over[0])
    return float(np.sum(fr_curve[:cut]) / cut)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch-size", type=int, default=512,
                        help="groups per forward pass (default: %(default)s, "
                             "which matches upstream's inference batch)")
    parser.add_argument("--no-amp", action="store_true",
                        help="disable fp16 autocast (upstream uses it)")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--save", default=None, help="write recon/gt to .npz")
    args = parser.parse_args()

    from ptychopinn_torch.helper import center_crop
    from ptychopinn_torch.reassembly import VectorizedBarycentricAccumulator

    meta = json.loads(cfg.META_FILE.read_text(encoding="utf-8"))
    with np.load(cfg.GROUPS_FILE, allow_pickle=False) as g:
        nn_indices = np.ascontiguousarray(g["nn_indices"])
        coords_global = np.ascontiguousarray(g["coords_global"], dtype=np.float32)
        com_np = np.ascontiguousarray(g["com"], dtype=np.float32)
        object_guess = np.array(g["object_guess"])

    N = int(meta["N"])
    C = int(meta["C"])
    middle = int(meta["middle_trim"])
    canvas_side = int(meta["canvas_side"])
    rms = float(meta["rms_scaling_constant"])
    window = int(meta["window"])
    n_groups = int(meta["n_groups"])

    device = torch.device(args.device)
    print(f"[dbg] groups={n_groups} N={N} C={C} middle_trim={middle} "
          f"canvas={canvas_side} rms={rms!r}")
    print(f"[dbg] com={com_np.tolist()}  "
          f"(x-y asymmetry {abs(float(com_np[0]) - float(com_np[1])):.4f} px)")
    print(f"[dbg] batch_size={args.batch_size} amp={not args.no_amp} device={device}")

    # --- diffraction data, exactly as PtychoDataset prepares it -------------
    with np.load(meta["npz_path"]) as npz:
        diff_stack = np.round(npz["diff3d"]).astype(np.float32)
    print(f"[dbg] diff3d={diff_stack.shape}")

    # --- model -------------------------------------------------------------
    import mlflow

    mlflow.set_tracking_uri(f"file:{cfg.MLRUNS_DIR.resolve()}")
    model = mlflow.pytorch.load_model(
        f"runs:/{meta['run_id']}/model", map_location=device
    )
    model.to(device)
    model.training = True
    print(f"[dbg] loaded {type(model).__name__}")

    # --- canvas ------------------------------------------------------------
    shape = (canvas_side, canvas_side)
    canvas = torch.zeros(shape, dtype=torch.complex64, device=device)
    counts = torch.zeros(shape, dtype=torch.float32, device=device)
    acc = VectorizedBarycentricAccumulator(shape, device)
    com = torch.from_numpy(com_np).to(device)
    canvas_center = torch.tensor([shape[1] // 2, shape[0] // 2],
                                 dtype=torch.float32, device=device)
    coords_t = torch.from_numpy(coords_global).to(device)

    cs = N // 2 - middle // 2
    ce = N // 2 + middle // 2

    with torch.no_grad():
        for start in range(0, n_groups, args.batch_size):
            end = min(start + args.batch_size, n_groups)
            idx = nn_indices[start:end]
            x = torch.from_numpy(
                np.ascontiguousarray(diff_stack[idx])
            ).to(device)                                   # (B, C, N, N)
            b = x.shape[0]
            in_scale = torch.full((b, 1, 1, 1), rms, dtype=torch.float32,
                                  device=device)

            if args.no_amp:
                out = model.forward_predict(x, None, None, in_scale)
            else:
                with torch.autocast(device_type=device.type, dtype=torch.float16):
                    out = model.forward_predict(x, None, None, in_scale)

            patches = out[:, :, cs:ce, cs:ce].to(torch.complex64)
            patches = patches.reshape(b * C, middle, middle)
            pos = coords_t[start:end].reshape(b * C, 2) - com.unsqueeze(0) \
                + canvas_center.unsqueeze(0)
            acc.accumulate_batch(canvas, counts, patches, pos, middle)

            if (start // args.batch_size) % 10 == 0:
                print(f"[dbg] {end}/{n_groups}")

    if device.type == "cuda":
        torch.cuda.synchronize()

    recon_full = (canvas / counts).cpu().numpy()
    w = window
    recon = recon_full[w:-w, w:-w]
    gt = center_crop(np.squeeze(object_guess)[w:-w, w:-w], recon.shape[0])
    n_nan = int(np.isnan(recon).sum())

    print(f"\n[dbg] recon={recon.shape} gt={gt.shape} nan_px_crop={n_nan}")
    if n_nan:
        print("[dbg] NaNs in crop; FRC undefined")
        return 1

    auc = frc_auc(gt, recon, cfg.FRC_AUC_CUTOFF, align=False)
    print(f"[dbg] OFFLINE FRC AUC (0..{cfg.FRC_AUC_CUTOFF}) = {auc:.6f}  "
          f"[align=False, the published setting]")

    # If registering the two images rescues the score, the reconstruction is
    # displaced, not degraded -- look at the centre of mass, not the model.
    try:
        auc_aligned = frc_auc(gt, recon, cfg.FRC_AUC_CUTOFF, align=True)
        print(f"[dbg] OFFLINE FRC AUC with registration = {auc_aligned:.6f}  "
              f"[align=True, diagnostic only]")
        if auc_aligned - auc > 0.05:
            print(f"[dbg] >>> registration recovers {auc_aligned - auc:+.4f}. "
                  "The reconstruction is SHIFTED relative to the ground truth, "
                  "not degraded. Suspect the canvas centre of mass "
                  f"(com={com_np.tolist()}) or the crop offsets.")
        else:
            print("[dbg] >>> registration does not help; the reconstruction "
                  "differs in content, not in position.")
    except Exception as exc:
        print(f"[dbg] aligned FRC failed: {exc}")

    if args.save:
        np.savez_compressed(args.save, reconstruction=recon, ground_truth=gt,
                            frc_auc=np.array(auc))
        print(f"[dbg] wrote {args.save}")

    print("\n[dbg] Interpretation:")
    print("[dbg]   close to upstream    -> prep + reassembly are fine,")
    print("[dbg]                           the bug is in the streaming path")
    print("[dbg]   close to the pipeline-> the bug is in prep or reassembly,")
    print("[dbg]                           transport is exonerated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
