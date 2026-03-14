import threading

import drava
import numpy as np
import tensorflow as tf
from keras.models import load_model

from config import (
    DATA_DIR,
    DRAVA_INFER_BATCH,
    PATCH_SIDE,
    STAGE1_JOB_ID,
    WT_DIR,
)
from pipeline_schema import encode_stage1_prediction


def configure_gpu_memory_growth() -> None:
    gpus = tf.config.experimental.list_physical_devices("GPU")
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Visible GPUs: {len(gpus)}, {gpus}")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as exc:
            drava.log(drava.DRAVA_VERBOSE_ERROR, f"Error in configuring gpu: {exc}")


configure_gpu_memory_growth()
drava.log(drava.DRAVA_VERBOSE_INFO, f"Built with CUDA: {tf.test.is_built_with_cuda()}")

min_epoch = int(np.load(f"{WT_DIR}/min_epoch.npy"))
MODEL_PATH = f"{WT_DIR}/weights.{min_epoch:02d}.hdf5"
model = load_model(MODEL_PATH)
drava.log(drava.DRAVA_VERBOSE_INFO, f"Loaded model: {MODEL_PATH}")
drava.log(drava.DRAVA_VERBOSE_INFO, f"Using dataset dir: {DATA_DIR}")

FRAME_DTYPE = np.float32
FRAME_BYTES = PATCH_SIDE * PATCH_SIDE * np.dtype(FRAME_DTYPE).itemsize
EOS_PREFIX = b"DRAVA_EOS:"
PUBLISH_CHUNK = 16

_next_start = 0
_expected_frames: int | None = None
_published_frames = 0
_state_lock = threading.Lock()
_predict_lock = threading.Lock()
_pending_raw: list[bytes] = []
_eos_raw: bytes | None = None
_eos_forwarded = False


def warmup_model(runs: int = 2, batch_size: int = DRAVA_INFER_BATCH) -> None:
    dummy = np.zeros((batch_size, PATCH_SIDE, PATCH_SIDE, 1), dtype=FRAME_DTYPE)
    for _ in range(runs):
        model.predict(dummy, verbose=0)
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Warmup done: runs={runs}, batch={batch_size}")


def func(frames) -> None:
    global _next_start, _published_frames, _expected_frames
    global _pending_raw, _eos_raw, _eos_forwarded

    info_line = None
    with _state_lock:
        for raw in frames:
            if raw.startswith(EOS_PREFIX):
                try:
                    eos_frames = int(raw[len(EOS_PREFIX):].decode("ascii"))
                except ValueError:
                    drava.log(drava.DRAVA_VERBOSE_WARN, f"Ignoring malformed EOS marker: {raw!r}")
                    continue
                prev = _expected_frames
                if (_expected_frames is None) or (eos_frames > _expected_frames):
                    _expected_frames = eos_frames
                    _eos_raw = raw
                if prev != _expected_frames:
                    info_line = f"EOS received: expected_frames={_expected_frames}"
                continue
            if len(raw) == 0:
                continue
            if len(raw) != FRAME_BYTES:
                raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")
            _pending_raw.append(raw)
    if info_line is not None:
        drava.log(drava.DRAVA_VERBOSE_INFO, info_line)

    while True:
        with _state_lock:
            run_batch = len(_pending_raw) >= DRAVA_INFER_BATCH
            flush_tail = (_eos_raw is not None) and (len(_pending_raw) > 0)
            if run_batch:
                batch_raw = _pending_raw[:DRAVA_INFER_BATCH]
                del _pending_raw[:DRAVA_INFER_BATCH]
            elif flush_tail:
                batch_raw = _pending_raw[:]
                _pending_raw.clear()
            else:
                batch_raw = []

            if batch_raw:
                batch_size = len(batch_raw)
                start = _next_start
                end = start + batch_size
                _next_start = end
                expected_for_payload = _expected_frames if _expected_frames is not None else 0

        if not batch_raw:
            break

        batch_size = len(batch_raw)
        stacked = b"".join(batch_raw)
        tensor = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
            (batch_size, PATCH_SIDE, PATCH_SIDE, 1), order="C"
        )

        with _predict_lock:
            pred_amp, pred_phi = model.predict(tensor, verbose=0)

        pred_amp_3d = pred_amp[..., 0]
        pred_phi_3d = pred_phi[..., 0]
        for off in range(0, batch_size, PUBLISH_CHUNK):
            chunk_end = min(off + PUBLISH_CHUNK, batch_size)
            payload = encode_stage1_prediction(
                job_id=STAGE1_JOB_ID,
                start=start + off,
                end=start + chunk_end,
                n_total=expected_for_payload,
                pred_amp=pred_amp_3d[off:chunk_end],
                pred_phi=pred_phi_3d[off:chunk_end],
            )

            rc = drava.publish_py(payload)
            if rc != drava.DRAVA_SUCCESS:
                raise RuntimeError(f"drava.publish_py() failed with rc={rc}")

        with _state_lock:
            _published_frames += batch_size

    with _state_lock:
        can_forward_eos = (
                (_eos_raw is not None)
                and (not _eos_forwarded)
                and (len(_pending_raw) == 0)
                and (_expected_frames is not None)
                and (_published_frames >= _expected_frames)
        )
        eos_to_send = _eos_raw if can_forward_eos else None
        if can_forward_eos:
            _eos_forwarded = True

    if eos_to_send is not None:
        rc = drava.publish_py(eos_to_send)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py(EOS) failed with rc={rc}")


warmup_model()

rc = drava.init()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(
        f"drava.init() failed with rc={rc}. "
        "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
    )

try:
    drava.register_routine_py(func)
    rc = drava.listen_py()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
finally:
    rc = drava.deinit()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.deinit() failed with rc={rc}")
