"""Offline preparation step for the PtychoPINN Drava example.

PtychoPINN is not frame-independent. Its published configuration is ``C=4`` with
``object_big=true``: one model input is a *group* of four spatially overlapping
diffraction patterns, selected by a KD-tree over the complete set of scan
positions. A frame cannot be grouped until all four of its quadrant neighbours
have arrived, so grouping cannot be done per-frame inside a streaming stage.

This script therefore does the grouping once, offline, and writes a compact
artifact that the publisher and both stages consume. It calls upstream's
*unmodified* ``group_coords`` / ``get_relative_coords`` / ``get_rms_scaling_factor``
so the physics and the normalisation are exactly the published ones.

What it deliberately does NOT do is go through ``PtychoDataset``. That class
pre-allocates a memory-mapped TensorDict from an *estimated* row count, while
``get_fixed_quadrant_neighbors_c4`` discards any centre lacking a neighbour in
all four quadrants. Upstream leaves the surplus rows zero-filled, and those
phantom rows carry ``coords_global == 0``, which inflates ``max_offset`` and
therefore the canvas size that the FRC crop is computed against. Sizing
everything from the *actual* group count here avoids that by construction --
the same defect the maintainer's repo fixes, without forking the package.

Usage (on a JLSE node, after download_zenodo.py and initialize_mlruns.py)::

    python prepare_dataset.py
    python prepare_dataset.py --dataset W --model PS_W
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import config as cfg


def _load_upstream():
    """Import ptychopinn_torch, with an actionable error if it is missing."""
    try:
        import torch  # noqa: F401
        from ptychopinn_torch import helper as hh
        from ptychopinn_torch.config_params import update_existing_config
        from ptychopinn_torch.patch_generator import (
            get_neighbor_indices,
            get_neighbors_indices_within_bounds,
            get_relative_coords,
            group_coords,
        )
        from ptychopinn_torch.utils import load_all_configs_from_mlflow
    except ImportError as exc:
        raise SystemExit(
            f"Could not import ptychopinn_torch ({exc}).\n"
            "Install the published package into the example venv, e.g.:\n"
            "    pip install -e /path/to/PtychoPINN-torch-pub\n"
            "See this example's README for the full JLSE setup."
        ) from exc
    return (
        hh,
        update_existing_config,
        get_neighbor_indices,
        get_neighbors_indices_within_bounds,
        get_relative_coords,
        group_coords,
        load_all_configs_from_mlflow,
    )


def _select_npz(dataset_dir: Path, experiment_number: int) -> Path:
    files = sorted(dataset_dir.glob("*.npz"))
    if not files:
        raise SystemExit(f"No .npz files found in {dataset_dir}")
    if experiment_number >= len(files):
        raise SystemExit(
            f"experiment_number={experiment_number} but only {len(files)} "
            f"npz file(s) in {dataset_dir}"
        )
    return files[experiment_number]


def _bounded_mask(xcoords, ycoords, x_bounds, y_bounds):
    """Reproduce PtychoDataset.calculate_length's coordinate bounding exactly."""
    xmin, xmax = float(np.min(xcoords)), float(np.max(xcoords))
    ymin, ymax = float(np.min(ycoords)), float(np.max(ycoords))

    x_range = xmax - xmin if xmax > xmin else 1.0
    y_range = ymax - ymin if ymax > ymin else 1.0

    x_lower = xmin + x_bounds[0] * x_range
    x_upper = xmin + x_bounds[1] * x_range
    y_lower = ymin + y_bounds[0] * y_range
    y_upper = ymin + y_bounds[1] * y_range

    if xmax <= xmin:
        x_upper = x_lower
    if ymax <= ymin:
        y_upper = y_lower

    mask = (
        (xcoords >= x_lower)
        & (xcoords <= x_upper)
        & (ycoords >= y_lower)
        & (ycoords <= y_upper)
    )
    return np.where(mask)[0], (xmin, xmax, ymin, ymax)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Group scan positions and precompute canvas geometry for the "
                    "PtychoPINN Drava example."
    )
    parser.add_argument("--dataset", default=cfg.DATASET,
                        help="dataset key, e.g. W (default: %(default)s)")
    parser.add_argument("--model", default=cfg.MODEL_KEY,
                        help="model key, e.g. PS_W (default: %(default)s)")
    parser.add_argument("--run-id", default=None,
                        help="MLflow run id; overrides --model")
    parser.add_argument("--dataset-dir", default=None,
                        help="directory holding the dataset npz files")
    parser.add_argument("--mlruns-dir", default=str(cfg.MLRUNS_DIR),
                        help="path to the unpacked mlruns tree")
    parser.add_argument("--out-dir", default=None,
                        help="output directory (default: prep/<dataset>_<model>)")
    parser.add_argument("--experiment-number", type=int, default=0,
                        help="index into the sorted npz list (default: %(default)s)")
    args = parser.parse_args()

    (
        hh,
        update_existing_config,
        get_neighbor_indices,
        get_neighbors_indices_within_bounds,
        get_relative_coords,
        group_coords,
        load_all_configs_from_mlflow,
    ) = _load_upstream()
    import torch

    run_id = args.run_id or cfg.MODEL_IDS.get(args.model, "")
    if not run_id:
        raise SystemExit(
            f"Unknown model key {args.model!r} and no --run-id given. "
            f"Known keys: {', '.join(sorted(cfg.MODEL_IDS))}"
        )

    dataset_dir = Path(args.dataset_dir) if args.dataset_dir else (
        cfg.DATA_ROOT / "data" / args.dataset
    )
    out_dir = Path(args.out_dir) if args.out_dir else (
        cfg.EXAMPLE_DIR / "prep" / f"{args.dataset}_{args.model}"
    )
    mlruns_dir = Path(args.mlruns_dir).resolve()
    if not mlruns_dir.is_dir():
        raise SystemExit(
            f"mlruns directory not found: {mlruns_dir}\n"
            "Unpack mlruns.tar.gz from Zenodo and run initialize_mlruns.py first."
        )

    tracking_uri = f"file:{mlruns_dir}"
    print(f"[prep] dataset={args.dataset} model={args.model} run_id={run_id}")
    print(f"[prep] tracking_uri={tracking_uri}")

    # ------------------------------------------------------------------ #
    # 1. Configs come from the model's own MLflow params, then get the same
    #    overrides recreate_results.ipynb applies in generate_gt_and_recon().
    # ------------------------------------------------------------------ #
    data_config, model_config, training_config, inference_config, _datagen = (
        load_all_configs_from_mlflow(run_id, tracking_uri)
    )

    bounds = [0.07, 0.93] if args.dataset in cfg.TIGHT_BOUNDS_DATASETS else [0.05, 0.95]
    update_existing_config(data_config, {
        "normalize": "Batch",
        "probe_normalize": "False",
        "n_subsample": 1,
        "x_bounds": bounds,
        "y_bounds": bounds,
    })
    update_existing_config(inference_config, {
        "middle_trim": data_config.N // 2,
        "experiment_number": args.experiment_number,
        "pad_eval": True,
    })

    if model_config.mode != "Unsupervised" or not model_config.object_big:
        raise SystemExit(
            f"This example targets the published unsupervised C={data_config.C} "
            f"configuration; got mode={model_config.mode!r} "
            f"object_big={model_config.object_big}."
        )

    print(f"[prep] N={data_config.N} C={data_config.C} "
          f"neighbor_function={data_config.neighbor_function} "
          f"normalize={data_config.normalize} bounds={bounds}")

    # ------------------------------------------------------------------ #
    # 2. Load the Ptychodus-formatted npz.
    # ------------------------------------------------------------------ #
    npz_path = _select_npz(dataset_dir, args.experiment_number)
    print(f"[prep] reading {npz_path}")
    with np.load(npz_path) as npz:
        diff3d = npz["diff3d"]
        xcoords_full = npz["xcoords"]
        ycoords_full = npz["ycoords"]
        object_guess = npz["objectGuess"]

    n_scans, h, w = diff3d.shape
    if h != data_config.N or w != data_config.N:
        raise SystemExit(
            f"diffraction patterns are {h}x{w} but the model expects "
            f"{data_config.N}x{data_config.N}"
        )
    print(f"[prep] n_scans={n_scans} pattern={h}x{w} "
          f"objectGuess={object_guess.shape}")

    # ------------------------------------------------------------------ #
    # 3. Coordinate bounding, then grouping via upstream's own functions.
    # ------------------------------------------------------------------ #
    valid_indices, extents = _bounded_mask(
        xcoords_full, ycoords_full, data_config.x_bounds, data_config.y_bounds
    )
    print(f"[prep] x_range={extents[0]:.4f}..{extents[1]:.4f} "
          f"y_range={extents[2]:.4f}..{extents[3]:.4f}")
    print(f"[prep] bounded centres: {len(valid_indices)} of {n_scans}")

    if data_config.neighbor_function == "Nearest":
        neighbor_function = get_neighbor_indices
    elif data_config.neighbor_function == "Min_dist":
        neighbor_function = get_neighbors_indices_within_bounds
    else:
        neighbor_function = "4_quadrant"

    nn_indices, coords_nn = group_coords(
        xcoords_full,
        ycoords_full,
        xcoords_full[valid_indices],
        ycoords_full[valid_indices],
        neighbor_function,
        valid_indices,
        data_config,
        C=data_config.C,
    )
    nn_indices = np.asarray(nn_indices, dtype=np.int64)
    n_groups = int(nn_indices.shape[0])
    print(f"[prep] grouped rows: {n_groups} "
          f"(estimated would have been {len(valid_indices) * data_config.n_subsample})")
    if n_groups == 0:
        raise SystemExit("Grouping produced zero valid groups; check the bounds.")

    coords_com, coords_relative = get_relative_coords(coords_nn)

    # coords_global: absolute scan positions of every member of every group.
    regular_global = np.stack([xcoords_full, ycoords_full], axis=1).astype(np.float32)
    coords_global = regular_global[nn_indices]            # (M, C, 2)

    # ------------------------------------------------------------------ #
    # 4. Normalisation constant. Under normalize='Batch' this is one scalar
    #    for the whole experiment, so a streaming stage can carry it as a
    #    constant without seeing the full stack.
    # ------------------------------------------------------------------ #
    diff_stack = torch.from_numpy(diff3d).round().to(torch.float32)
    rms_scale = hh.get_rms_scaling_factor(diff_stack, data_config)
    rms_scale = float(np.asarray(rms_scale).reshape(-1)[0])
    print(f"[prep] batch rms scaling constant = {rms_scale!r}")

    # ------------------------------------------------------------------ #
    # 5. Canvas geometry, matching reconstruct_image_barycentric().
    #
    # Careful here. Upstream reads:
    #
    #     if 'com' in ptycho_subset.data_dict:
    #         center_of_mass = torch.mean(global_coords, dim=...)
    #     else:
    #         center_of_mass = ptycho_subset.data_dict['com']
    #
    # The condition is inverted, and memory_map_data always sets
    # data_dict['com'], so the *mean over coords_global* branch is the one that
    # always runs and the stored value is dead code. The two differ: the stored
    # com is the mean of the bounded scan positions, whereas coords_global
    # includes neighbours just outside the bounds and weights each position by
    # how many groups it belongs to. We reproduce the branch that actually
    # executes, because that is what produced the published canvas.
    # ------------------------------------------------------------------ #
    com = coords_global.astype(np.float64).mean(axis=(0, 1))
    com_bounded = np.array(
        [xcoords_full[valid_indices].mean(), ycoords_full[valid_indices].mean()],
        dtype=np.float64,
    )
    adjusted = coords_global.astype(np.float64) - com
    max_offset = int(np.ceil(np.max(np.abs(adjusted))))
    middle_trim = int(inference_config.middle_trim)
    canvas_side = middle_trim + 2 * max_offset
    print(f"[prep] com={com} (dead-branch bounded com would be {com_bounded})")
    print(f"[prep] max_offset={max_offset} "
          f"canvas={canvas_side}x{canvas_side} middle_trim={middle_trim}")

    # ------------------------------------------------------------------ #
    # 6. Write artifacts.
    # ------------------------------------------------------------------ #
    out_dir.mkdir(parents=True, exist_ok=True)
    groups_path = out_dir / "groups.npz"
    meta_path = out_dir / "meta.json"

    np.savez(
        groups_path,
        nn_indices=nn_indices,
        coords_global=coords_global.astype(np.float32),
        coords_relative=coords_relative.astype(np.float32),
        coords_center=coords_com.astype(np.float32),
        com=com.astype(np.float32),
        com_bounded=com_bounded.astype(np.float32),
        object_guess=object_guess,
    )

    meta = {
        "schema_version": 1,
        "dataset": args.dataset,
        "model_key": args.model,
        "run_id": run_id,
        "npz_path": str(npz_path),
        "mlruns_dir": str(mlruns_dir),
        "n_scans": int(n_scans),
        "n_groups": n_groups,
        "n_bounded_centres": int(len(valid_indices)),
        "N": int(data_config.N),
        "C": int(data_config.C),
        "middle_trim": middle_trim,
        "max_offset": max_offset,
        "canvas_side": int(canvas_side),
        "rms_scaling_constant": rms_scale,
        "com": [float(com[0]), float(com[1])],
        "com_bounded_unused": [float(com_bounded[0]), float(com_bounded[1])],
        "x_bounds": list(data_config.x_bounds),
        "y_bounds": list(data_config.y_bounds),
        "neighbor_function": str(data_config.neighbor_function),
        "normalize": str(data_config.normalize),
        "frame_bytes": int(data_config.C * data_config.N * data_config.N * 4),
        "window": int(cfg.WINDOW_SIZES.get(args.dataset, inference_config.window)),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"[prep] wrote {groups_path}")
    print(f"[prep] wrote {meta_path}")
    print(f"[prep] publisher frame size = {meta['frame_bytes']} bytes "
          f"({data_config.C}x{data_config.N}x{data_config.N} float32)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
