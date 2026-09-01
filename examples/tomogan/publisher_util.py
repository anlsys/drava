"""TomoGAN publisher helpers.

Generic publisher plumbing (config resolution, metrics, EOS, pacing) now lives
in ``drava_common``; this module only keeps the TomoGAN-specific dataset payload
loading and thin wrappers that re-export the shared helpers.
"""
import os
import sys

import numpy as np
import h5py

from config import DATASET_PATH, TEST_INPUT_KEY

# Make the shared examples/common package importable without installation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from drava_common import (  # noqa: E402
    load_publish_config as _load_publish_config,
    load_transport_config,
    write_publisher_metrics,
)

__all__ = [
    "load_transport_config",
    "load_publish_config",
    "write_publisher_metrics",
    "load_dataset_payloads",
]


def _dataset_frame_count():
    if DATASET_PATH.exists():
        with h5py.File(DATASET_PATH, "r") as h5fd:
            return int(h5fd[TEST_INPUT_KEY].shape[0])
    return None


def load_publish_config():
    """Return ``(rate_hz, num_frames)`` for TomoGAN.

    TomoGAN publishes the real dataset (no synthetic mode), defaulting the frame
    count to the dataset size when neither env nor YAML specifies it.
    """
    rate_hz, _synthetic, num_frames = _load_publish_config(
        default_num_frames=_dataset_frame_count()
    )
    return rate_hz, num_frames


def load_dataset_payloads():
    if not DATASET_PATH.exists():
        raise RuntimeError(f"TomoGAN dataset not found: {DATASET_PATH}")
    with h5py.File(DATASET_PATH, "r") as h5fd:
        frames = h5fd[TEST_INPUT_KEY][:].astype(np.float32)
    payloads = [frame.tobytes(order="C") for frame in frames]
    if not payloads:
        raise RuntimeError(
            f"No frames found in dataset {DATASET_PATH}:{TEST_INPUT_KEY}"
        )
    return payloads
