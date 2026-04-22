import os
from pathlib import Path

import h5py


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


EXAMPLE_DIR = Path(__file__).resolve().parent
DATASET_PATH = Path(
    os.getenv(
        "TOMOGAN_DATASET_PATH",
        str(EXAMPLE_DIR / "dataset" / "demo-dataset-real.h5"),
    )
)
MODEL_PATH = os.getenv(
    "DRAVA_TOMOGAN_MODEL_PATH",
    os.getenv(
        "TOMOGAN_MODEL_PATH",
        str(EXAMPLE_DIR / "dataset" / "testjob-it00500.h5"),
    ),
)
OUTPUT_PATH = Path(
    os.getenv(
        "DRAVA_TOMOGAN_OUTPUT_PATH",
        str(EXAMPLE_DIR / "drava_tomogan_output.h5"),
    )
)

TEST_INPUT_KEY = os.getenv("DRAVA_TOMOGAN_INPUT_KEY", "test_ns")
TEST_TARGET_KEY = os.getenv("DRAVA_TOMOGAN_TARGET_KEY", "test_gt")


def _infer_frame_shape() -> tuple[int, int]:
    if not DATASET_PATH.exists():
        fallback_h = _get_int("DRAVA_FRAME_HEIGHT", 1024)
        fallback_w = _get_int("DRAVA_FRAME_WIDTH", 1024)
        return fallback_h, fallback_w

    with h5py.File(DATASET_PATH, "r") as h5fd:
        if TEST_INPUT_KEY not in h5fd:
            raise KeyError(f"dataset key {TEST_INPUT_KEY!r} not found in {DATASET_PATH}")
        shape = tuple(int(x) for x in h5fd[TEST_INPUT_KEY].shape)

    if len(shape) != 3:
        raise ValueError(
            f"expected {TEST_INPUT_KEY} to have shape (N,H,W), got {shape}"
        )
    return shape[1], shape[2]


FRAME_HEIGHT, FRAME_WIDTH = _infer_frame_shape()
FRAME_DTYPE = "float32"
FRAME_BYTES = FRAME_HEIGHT * FRAME_WIDTH * 4

DRAVA_INFER_BATCH = _get_int("DRAVA_INFER_BATCH", 16)
LOG_EVERY = _get_int("DRAVA_LOG_EVERY", DRAVA_INFER_BATCH)
