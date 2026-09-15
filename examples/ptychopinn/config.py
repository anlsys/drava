"""App-side constants for the PtychoPINN example.

Mirrors the PtychoNN example's convention: runtime knobs (threads, batching,
transport, streams) live in ``pipeline.yaml`` and are read by the Drava runtime;
everything here is app-level and comes from environment variables with a
sensible default.

The Zenodo bundle (DOI 10.5281/zenodo.16968020) unpacks into ``DATA_ROOT`` as::

    PtychoPINN_data/
        data/<DATASET>/*.npz     # diff3d, xcoords, ycoords, probeGuess, objectGuess
        mlruns/<experiment>/<run_id>/artifacts/model/
"""
import os
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _get_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return Path(raw)


# --------------------------------------------------------------------------- #
# Published model registry (paper Figure 2 transfer experiments).
#
# Run ids are MLflow run hashes inside mlruns.tar.gz. "PS_" = dead-leaves
# synthetic pretrain, "PE_" = experiment-only. The remaining multi-probe and
# synthetic-object models from the paper are listed in the upstream
# recreate_results.ipynb; add them here if you need them.
# --------------------------------------------------------------------------- #
MODEL_IDS = {
    # Dead-leaves synthetic pretrain, single-experiment transfer (Figure 2)
    "PS_TP1": "f637381fd7fe49158bb0ed2e7a28ca45",
    "PS_TP2": "6fb4668f21e44e0b80056f64fdfedf01",
    "PS_IC1": "345aa234e8f34935af11c3ebed167448",
    "PS_IC2": "06822d7239504a93ae0f7a6c4577cdc8",
    "PS_NCM": "0908cd113f774d15802f41e40b3a51e2",
    "PS_FLY1": "3d2ca583357c43baa6ab17519d500355",
    "PS_W": "74ba23396c4042afb1751afe9fa87520",
    "PS_LFP": "1cda8280703748fabba173f747fc4103",
    # Experiment-only, single-experiment transfer (Figure 2)
    "PE_TP1": "c86ba4cc6d424a8fb1370bcfa87d967c",
    "PE_TP2": "3dcc4ce0423c46f6bab529294886f453",
    "PE_IC1": "b1f8f06f9dee41e48e0323d295e0a5d3",
    "PE_IC2": "e09fa3d8b48e406aa7c9ff78e34f7782",
    "PE_NCM": "293d4107954d4d11832fe979e6045229",
    "PE_FLY1": "4911939f91d147348f450ec1d78811dd",
    "PE_W": "3360765d399443d0a758e9667c8455b5",
    "PE_LFP": "aee5ab755d8e4e558c1f328491adb0fb",
}

# Per-dataset crop applied before the FRC, from recreate_results.ipynb.
WINDOW_SIZES = {
    "TP1": 20, "TP2": 40, "IC1": 20, "IC2": 20,
    "NCM": 20, "FLY1": 10, "W": 20, "LFP": 20,
}

# Datasets whose edges are trimmed harder; see generate_gt_and_recon() upstream.
TIGHT_BOUNDS_DATASETS = ("TP1", "IC1")

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
DATA_ROOT = _get_path("PTYCHOPINN_DATA_ROOT", EXAMPLE_DIR / "PtychoPINN_data")
MLRUNS_DIR = _get_path("PTYCHOPINN_MLRUNS_DIR", DATA_ROOT / "mlruns")

DATASET = os.getenv("PTYCHOPINN_DATASET", "W")
DATASET_DIR = _get_path("PTYCHOPINN_DATASET_DIR", DATA_ROOT / "data" / DATASET)

MODEL_KEY = os.getenv("PTYCHOPINN_MODEL", "PS_W")
RUN_ID = os.getenv("PTYCHOPINN_RUN_ID", "") or MODEL_IDS.get(MODEL_KEY, "")

# prepare_dataset.py writes here; the publisher and both stages read it.
PREP_DIR = _get_path("PTYCHOPINN_PREP_DIR", EXAMPLE_DIR / "prep" / f"{DATASET}_{MODEL_KEY}")
GROUPS_FILE = PREP_DIR / "groups.npz"
META_FILE = PREP_DIR / "meta.json"

# --------------------------------------------------------------------------- #
# Tensor geometry. Defaults match the published 64x64 / C=4 configuration; the
# authoritative values are written to meta.json by prepare_dataset.py, which
# reads them from the model's own MLflow config.
# --------------------------------------------------------------------------- #
PATCH_SIDE = _get_int("DRAVA_PATCH_SIDE", 64)
GROUP_SIZE = _get_int("DRAVA_GROUP_SIZE", 4)
MIDDLE_TRIM = _get_int("DRAVA_MIDDLE_TRIM", PATCH_SIDE // 2)

DRAVA_INFER_BATCH = _get_int("DRAVA_INFER_BATCH", 128)
LOG_EVERY = _get_int("DRAVA_LOG_EVERY", DRAVA_INFER_BATCH)
STAGE1_JOB_ID = _get_int("DRAVA_STAGE1_JOB_ID", 1)

# Torch device for stage1 inference. The published reconstruction path runs
# FP16 autocast on CUDA; see README for why this is not softened to a fallback.
TORCH_DEVICE = os.getenv("PTYCHOPINN_DEVICE", "cuda")
USE_MIXED_PRECISION = os.getenv("PTYCHOPINN_MIXED_PRECISION", "1") == "1"

# Stage-2 evaluation.
FRC_WINDOW = _get_int("PTYCHOPINN_FRC_WINDOW", WINDOW_SIZES.get(DATASET, 20))
FRC_AUC_CUTOFF = _get_float("PTYCHOPINN_FRC_AUC_CUTOFF", 0.5)
SAVE_RECON = os.getenv("PTYCHOPINN_SAVE_RECON", "1") == "1"
RECON_PATH = _get_path("PTYCHOPINN_RECON_PATH", PREP_DIR / "reconstruction.npz")
