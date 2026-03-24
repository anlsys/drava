import json
import struct
from typing import Any

import numpy as np

SCHEMA_VERSION = 1
_HEADER_LEN_FMT = "!I"
_HEADER_LEN_SIZE = struct.calcsize(_HEADER_LEN_FMT)


def encode_stage1_prediction(
        *,
        job_id: int,
        start: int,
        end: int,
        n_total: int,
        pred_amp: np.ndarray,
        pred_phi: np.ndarray,
) -> bytes:
    amp = np.asarray(pred_amp, dtype=np.float32)
    phi = np.asarray(pred_phi, dtype=np.float32)

    if amp.shape != phi.shape:
        raise ValueError(f"shape mismatch: amp={amp.shape}, phi={phi.shape}")
    if amp.ndim != 3:
        raise ValueError(f"expected (B,H,W), got shape={amp.shape}")
    if (end - start) != amp.shape[0]:
        raise ValueError(
            f"batch range mismatch: range={end - start}, batch={amp.shape[0]}"
        )

    amp_bytes = amp.tobytes(order="C")
    phi_bytes = phi.tobytes(order="C")

    header = {
        "schema_version": SCHEMA_VERSION,
        "kind": "stage1_prediction_batch",
        "job_id": int(job_id),
        "start": int(start),
        "end": int(end),
        "n_total": int(n_total),
        "dtype": "float32",
        "shape": list(amp.shape),
        "amp_nbytes": len(amp_bytes),
        "phi_nbytes": len(phi_bytes),
    }
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    if len(header_bytes) > (2 ** 32 - 1):
        raise ValueError("header too large")

    return struct.pack(_HEADER_LEN_FMT, len(header_bytes)) + header_bytes + amp_bytes + phi_bytes


def decode_stage1_prediction(payload: bytes) -> dict[str, Any]:
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
    if header.get("kind") != "stage1_prediction_batch":
        raise ValueError(f"unexpected kind: {header.get('kind')}")
    if header.get("dtype") != "float32":
        raise ValueError(f"unsupported dtype: {header.get('dtype')}")

    shape = tuple(int(x) for x in header["shape"])
    if len(shape) != 3:
        raise ValueError(f"expected 3D shape, got {shape}")

    amp_nbytes = int(header["amp_nbytes"])
    phi_nbytes = int(header["phi_nbytes"])
    amp_start = end_header
    amp_end = amp_start + amp_nbytes
    phi_start = amp_end
    phi_end = phi_start + phi_nbytes

    if phi_end != len(payload):
        raise ValueError(
            f"payload size mismatch: expected={phi_end} actual={len(payload)}"
        )

    amp = np.frombuffer(payload[amp_start:amp_end], dtype=np.float32).reshape(shape, order="C")
    phi = np.frombuffer(payload[phi_start:phi_end], dtype=np.float32).reshape(shape, order="C")

    return {
        "job_id": int(header["job_id"]),
        "start": int(header["start"]),
        "end": int(header["end"]),
        "n_total": int(header["n_total"]),
        "pred_amp": amp,
        "pred_phi": phi,
    }
