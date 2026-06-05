from __future__ import annotations

import time
from typing import Any

import numpy as np


FRAME_CHANNEL = "ptychonn:frames"
OUTPUT_CHANNEL = "ptychonn:stage1"
FRAME_DTYPE = np.float32
PATCH_SIDE = 64
FRAME_SHAPE = (PATCH_SIDE, PATCH_SIDE, 1)
FRAME_BYTES = PATCH_SIDE * PATCH_SIDE * np.dtype(FRAME_DTYPE).itemsize


def now_ns() -> int:
    return time.time_ns()


def _ubyte_array_from_bytes(payload: bytes) -> np.ndarray:
    return np.frombuffer(payload, dtype=np.uint8)


def frame_structure(pvaccess: Any) -> dict[str, Any]:
    return {
        "uniqueId": pvaccess.LONG,
        "timestampNs": pvaccess.LONG,
        "eos": pvaccess.BOOLEAN,
        "nTotal": pvaccess.LONG,
        "dtype": pvaccess.STRING,
        "height": pvaccess.INT,
        "width": pvaccess.INT,
        "channels": pvaccess.INT,
        "payload": [pvaccess.UBYTE],
    }


def prediction_structure(pvaccess: Any) -> dict[str, Any]:
    return {
        "uniqueId": pvaccess.LONG,
        "timestampNs": pvaccess.LONG,
        "eos": pvaccess.BOOLEAN,
        "jobId": pvaccess.LONG,
        "start": pvaccess.LONG,
        "end": pvaccess.LONG,
        "nTotal": pvaccess.LONG,
        "payload": [pvaccess.UBYTE],
    }


def make_initial_frame_object(pvaccess: Any) -> Any:
    return pvaccess.PvObject(
        frame_structure(pvaccess),
        {
            "uniqueId": -1,
            "timestampNs": now_ns(),
            "eos": False,
            "nTotal": 0,
            "dtype": "float32",
            "height": PATCH_SIDE,
            "width": PATCH_SIDE,
            "channels": 1,
            "payload": np.empty((0,), dtype=np.uint8),
        },
    )


def make_frame_object(pvaccess: Any, unique_id: int, n_total: int, payload: bytes) -> Any:
    if len(payload) != FRAME_BYTES:
        raise ValueError(f"payload mismatch: got {len(payload)} bytes, expected {FRAME_BYTES}")
    return pvaccess.PvObject(
        frame_structure(pvaccess),
        {
            "uniqueId": int(unique_id),
            "timestampNs": now_ns(),
            "eos": False,
            "nTotal": int(n_total),
            "dtype": "float32",
            "height": PATCH_SIDE,
            "width": PATCH_SIDE,
            "channels": 1,
            "payload": _ubyte_array_from_bytes(payload),
        },
    )


def make_eos_frame_object(pvaccess: Any, unique_id: int, n_total: int) -> Any:
    return pvaccess.PvObject(
        frame_structure(pvaccess),
        {
            "uniqueId": int(unique_id),
            "timestampNs": now_ns(),
            "eos": True,
            "nTotal": int(n_total),
            "dtype": "float32",
            "height": PATCH_SIDE,
            "width": PATCH_SIDE,
            "channels": 1,
            "payload": np.empty((0,), dtype=np.uint8),
        },
    )


def make_initial_prediction_object(pvaccess: Any) -> Any:
    return pvaccess.PvObject(
        prediction_structure(pvaccess),
        {
            "uniqueId": -1,
            "timestampNs": now_ns(),
            "eos": False,
            "jobId": 0,
            "start": 0,
            "end": 0,
            "nTotal": 0,
            "payload": np.empty((0,), dtype=np.uint8),
        },
    )


def make_prediction_object(
    pvaccess: Any,
    *,
    unique_id: int,
    job_id: int,
    start: int,
    end: int,
    n_total: int,
    payload: bytes,
) -> Any:
    return pvaccess.PvObject(
        prediction_structure(pvaccess),
        {
            "uniqueId": int(unique_id),
            "timestampNs": now_ns(),
            "eos": False,
            "jobId": int(job_id),
            "start": int(start),
            "end": int(end),
            "nTotal": int(n_total),
            "payload": _ubyte_array_from_bytes(payload),
        },
    )


def make_eos_prediction_object(pvaccess: Any, unique_id: int, n_total: int) -> Any:
    return pvaccess.PvObject(
        prediction_structure(pvaccess),
        {
            "uniqueId": int(unique_id),
            "timestampNs": now_ns(),
            "eos": True,
            "jobId": 0,
            "start": int(n_total),
            "end": int(n_total),
            "nTotal": int(n_total),
            "payload": np.empty((0,), dtype=np.uint8),
        },
    )


def pv_field(pv_object: Any, field_name: str) -> Any:
    try:
        return pv_object.getPyObject(field_name)
    except Exception:
        return pv_object[field_name]


def payload_bytes_from_pv(pv_object: Any) -> bytes:
    value = pv_field(pv_object, "payload")
    if isinstance(value, bytes):
        return value
    arr = np.asarray(value, dtype=np.uint8)
    return arr.tobytes(order="C")
