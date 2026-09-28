"""Wire format between PtychoPINN stage1 and stage2.

Same shape as the PtychoNN example's schema: a 4-byte big-endian header length,
a JSON header, then raw little-endian-native float32 blobs. Here the payload is
the complex object patch predicted by ``forward_predict``, split into real and
imaginary parts so the dtype on the wire stays plain float32.

Patches are ``(B, C, M, M)`` where ``B`` is the number of scan-position groups
in this chunk, ``C`` is the group size (4 in the published config), and ``M`` is
``middle_trim`` -- the center crop that stage2 splats onto the canvas.

Each chunk carries an explicit ``indices`` array giving the absolute group
index of every patch, rather than a ``[start, end)`` range derived from the
runtime's ``base_index``. That range is unsound under parallel callbacks: with
``callback_serialize: false`` the runtime assigns ``base_index`` via an atomic
fetch_add *inside* the spawned task (src/drava_internal.cc:601), so batches can
be numbered in task-execution order rather than arrival order. Explicit indices
also survive JetStream reordering and redelivery.
"""
import json
import struct
from typing import Any

import numpy as np

SCHEMA_VERSION = 2
_HEADER_LEN_FMT = "!I"
_HEADER_LEN_SIZE = struct.calcsize(_HEADER_LEN_FMT)
_KIND = "stage1_patch_batch"


def encode_stage1_patches(
        *,
        job_id: int,
        indices: np.ndarray,
        n_total: int,
        patches: np.ndarray,
) -> bytes:
    """Encode complex object patches together with their group indices."""
    patches = np.asarray(patches)
    if patches.ndim != 4:
        raise ValueError(f"expected (B,C,M,M), got shape={patches.shape}")

    idx = np.ascontiguousarray(indices, dtype=np.int64)
    if idx.ndim != 1:
        raise ValueError(f"expected 1-D indices, got shape={idx.shape}")
    if idx.shape[0] != patches.shape[0]:
        raise ValueError(
            f"index/patch count mismatch: {idx.shape[0]} vs {patches.shape[0]}"
        )

    real = np.ascontiguousarray(patches.real, dtype=np.float32)
    imag = np.ascontiguousarray(patches.imag, dtype=np.float32)

    idx_bytes = idx.tobytes(order="C")
    real_bytes = real.tobytes(order="C")
    imag_bytes = imag.tobytes(order="C")

    header = {
        "schema_version": SCHEMA_VERSION,
        "kind": _KIND,
        "job_id": int(job_id),
        "count": int(idx.shape[0]),
        "n_total": int(n_total),
        "dtype": "float32",
        "index_dtype": "int64",
        "shape": list(real.shape),
        "indices_nbytes": len(idx_bytes),
        "real_nbytes": len(real_bytes),
        "imag_nbytes": len(imag_bytes),
    }
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > (2 ** 32 - 1):
        raise ValueError("header too large")

    return (
        struct.pack(_HEADER_LEN_FMT, len(header_bytes))
        + header_bytes
        + idx_bytes
        + real_bytes
        + imag_bytes
    )


def decode_stage1_patches(payload: bytes) -> dict[str, Any]:
    """Inverse of :func:`encode_stage1_patches`. Returns complex64 patches."""
    if len(payload) < _HEADER_LEN_SIZE:
        raise ValueError("payload too small for header length")

    (header_len,) = struct.unpack_from(_HEADER_LEN_FMT, payload, 0)
    off = _HEADER_LEN_SIZE
    end_header = off + header_len
    if end_header > len(payload):
        raise ValueError("header length exceeds payload size")

    header = json.loads(payload[off:end_header].decode("utf-8"))
    if header.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema version: {header.get('schema_version')}")
    if header.get("kind") != _KIND:
        raise ValueError(f"unexpected kind: {header.get('kind')}")
    if header.get("dtype") != "float32":
        raise ValueError(f"unsupported dtype: {header.get('dtype')}")

    if header.get("index_dtype") != "int64":
        raise ValueError(f"unsupported index dtype: {header.get('index_dtype')}")

    shape = tuple(int(x) for x in header["shape"])
    if len(shape) != 4:
        raise ValueError(f"expected 4D shape, got {shape}")

    idx_nbytes = int(header["indices_nbytes"])
    real_nbytes = int(header["real_nbytes"])
    imag_nbytes = int(header["imag_nbytes"])

    idx_start = end_header
    idx_end = idx_start + idx_nbytes
    real_start = idx_end
    real_end = real_start + real_nbytes
    imag_start = real_end
    imag_end = imag_start + imag_nbytes

    if imag_end != len(payload):
        raise ValueError(
            f"payload size mismatch: expected={imag_end} actual={len(payload)}"
        )

    indices = np.frombuffer(payload[idx_start:idx_end], dtype=np.int64)
    if indices.shape[0] != shape[0]:
        raise ValueError(
            f"index/patch count mismatch: {indices.shape[0]} vs {shape[0]}"
        )

    real = np.frombuffer(payload[real_start:real_end], dtype=np.float32).reshape(
        shape, order="C"
    )
    imag = np.frombuffer(payload[imag_start:imag_end], dtype=np.float32).reshape(
        shape, order="C"
    )

    return {
        "job_id": int(header["job_id"]),
        "indices": indices.copy(),
        "n_total": int(header["n_total"]),
        "patches": (real + 1j * imag).astype(np.complex64),
    }
