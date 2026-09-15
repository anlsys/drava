"""PtychoPINN publisher helpers.

Generic publisher plumbing (config resolution, metrics, EOS, pacing) lives in
``drava_common``; this module only keeps the PtychoPINN-specific payload
generator and thin wrappers that re-export the shared helpers.

One payload is one *scan-position group*: ``C x N x N`` float32, row-major, the
diffraction patterns of the C overlapping positions selected offline by
prepare_dataset.py. Payloads are built lazily -- materialising all of them would
cost several GB because every frame belongs to many groups.
"""
import json
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

import config as cfg  # noqa: E402

SYNTHETIC_SEED = 56465
SYNTHETIC_POOL_SIZE = 512

__all__ = [
    "load_transport_config",
    "load_publish_config",
    "write_publisher_metrics",
    "make_payload_generator",
    "read_meta",
]


def read_meta():
    """Return the prep metadata dict, or ``None`` if prep has not been run."""
    try:
        return json.loads(cfg.META_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_publish_config():
    """Return ``(rate_hz, synthetic_mode, num_frames)`` for PtychoPINN.

    Defaults ``num_frames`` to the prepared group count so a plain run streams
    the whole scan exactly once.
    """
    meta = read_meta()
    default_num_frames = meta.get("n_groups") if meta else None
    return _load_publish_config(default_num_frames=default_num_frames)


def make_payload_generator(synthetic_mode):
    meta = read_meta()
    if meta is None:
        raise RuntimeError(
            f"Missing prep metadata: {cfg.META_FILE}\n"
            "Run prepare_dataset.py before starting the publisher."
        )

    group_size = int(meta["C"])
    patch_side = int(meta["N"])

    if synthetic_mode:
        rng = np.random.default_rng(SYNTHETIC_SEED)
        pool = rng.random(
            (SYNTHETIC_POOL_SIZE, group_size, patch_side, patch_side), dtype=np.float32
        )
        payloads = [group.tobytes(order="C") for group in pool]

        def next_payload(i):
            return payloads[i % SYNTHETIC_POOL_SIZE]

        return next_payload

    with np.load(cfg.GROUPS_FILE, allow_pickle=False) as groups:
        nn_indices = np.ascontiguousarray(groups["nn_indices"])

    # Rounding matches PtychoDataset: raw counts from non-photon detectors are
    # rounded before normalisation.
    with np.load(meta["npz_path"]) as npz:
        diff_stack = np.round(npz["diff3d"]).astype(np.float32)

    n_groups = int(nn_indices.shape[0])

    def next_payload(i):
        idx = nn_indices[i % n_groups]
        return np.ascontiguousarray(diff_stack[idx]).tobytes(order="C")

    return next_payload
