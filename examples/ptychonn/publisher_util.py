"""PtychoNN publisher helpers.

Generic publisher plumbing (config resolution, metrics, EOS, pacing) now lives
in ``drava_common``; this module only keeps the PtychoNN-specific payload
generator and thin wrappers that re-export the shared helpers so existing
imports keep working.
"""
import os
import sys

import numpy as np

# Make the shared examples/common package importable without installation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from drava_common import (  # noqa: E402
    load_publish_config as _load_publish_config,
    load_transport_config,
    write_publisher_metrics,
)

DATA_DIR = "PtychoNN_data_partial"
FRAME_SHAPE = (64, 64, 1)
SYNTHETIC_SEED = 56465
SYNTHETIC_POOL_SIZE = 3600

__all__ = [
    "load_transport_config",
    "load_publish_config",
    "write_publisher_metrics",
    "make_payload_generator",
]


def load_publish_config():
    """Return ``(rate_hz, synthetic_mode, num_frames)`` for PtychoNN."""
    return _load_publish_config()


def make_payload_generator(synthetic_mode):
    if synthetic_mode:
        rng = np.random.default_rng(SYNTHETIC_SEED)
        synthetic_frames = rng.random(
            (SYNTHETIC_POOL_SIZE, *FRAME_SHAPE), dtype=np.float32
        )
        payloads = [frame.tobytes(order="C") for frame in synthetic_frames]

        def next_payload(i):
            return payloads[i % SYNTHETIC_POOL_SIZE]

        return next_payload

    x_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")
    payloads = [frame.tobytes(order="C") for frame in x_test]
    n_frames = len(payloads)

    def next_payload(i):
        return payloads[i % n_frames]

    return next_payload
