"""Wire format between PtychoPINN stage1 and stage2.

Same shape as the PtychoNN example's schema: a 4-byte big-endian header length,
a JSON header, then raw little-endian-native float32 blobs. Here the payload is
the complex object patch predicted by ``forward_predict``, split into real and
imaginary parts so the dtype on the wire stays plain float32.

Patches are ``(B, C, M, M)`` where ``B`` is the number of scan-position groups
in this chunk, ``C`` is the group size (4 in the published config), and ``M`` is
``middle_trim`` -- the center crop that stage2 splats onto the canvas.
"""
import json
import struct
from typing import Any

import numpy as np

SCHEMA_VERSION = 1
_HEADER_LEN_FMT = "!I"
_HEADER_LEN_SIZE = struct.calcsize(_HEADER_LEN_FMT)
_KIND = "stage1_patch_batch"


def encode_stage1_patches(
        *,
        job_id: int,
        start: int,
        end: int,
        n_total: int,
        patches: np.ndarray,
) -> bytes:
    """Encode a chunk of complex object patches for groups ``[start, end)``."""
    patches = np.asarray(patches)
    if patches.ndim != 4:
        raise ValueError(f"expected (B,C,M,M), got shape={patches.shape}")
    if (end - start) != patches.shape[0]:
        raise ValueError(
            f"group range mismatch: range={end - start}, batch={patches.shape[0]}"
        )

    real = np.ascontiguousarray(patches.real, dtype=np.float32)
    imag = np.ascontiguousarray(patches.imag, dtype=np.float32)

    real_bytes = real.tobytes(order="C")
    imag_bytes = imag.tobytes(order="C")

    header = {
        "schema_version": SCHEMA_VERSION,
        "kind": _KIND,
        "job_id": int(job_id),
        "start": int(start),
        "end": int(end),
        "n_total": int(n_total),
        "dtype": "float32",
        "shape": list(real.shape),
        "real_nbytes": len(real_bytes),
        "imag_nbytes": len(imag_bytes),
    }
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > (2 ** 32 - 1):
        raise ValueError("header too large")

    return (
        struct.pack(_HEADER_LEN_FMT, len(header_bytes))
        + header_bytes
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

    shape = tuple(int(x) for x in header["shape"])
    if len(shape) != 4:
        raise ValueError(f"expected 4D shape, got {shape}")

    real_nbytes = int(header["real_nbytes"])
    imag_nbytes = int(header["imag_nbytes"])
    real_start = end_header
    real_end = real_start + real_nbytes
    imag_start = real_end
    imag_end = imag_start + imag_nbytes

    if imag_end != len(payload):
        raise ValueError(
            f"payload size mismatch: expected={imag_end} actual={len(payload)}"
        )

    real = np.frombuffer(payload[real_start:real_end], dtype=np.float32).reshape(
        shape, order="C"
    )
    imag = np.frombuffer(payload[imag_start:imag_end], dtype=np.float32).reshape(
        shape, order="C"
    )

    return {
        "job_id": int(header["job_id"]),
        "start": int(header["start"]),
        "end": int(header["end"]),
        "n_total": int(header["n_total"]),
        "patches": (real + 1j * imag).astype(np.complex64),
    }
