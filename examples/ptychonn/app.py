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
drava.log(drava.DRAVA_VERBOSE_INFO, f"Using model assets dir: {DATA_DIR}")

FRAME_DTYPE = np.float32
FRAME_BYTES = PATCH_SIDE * PATCH_SIDE * np.dtype(FRAME_DTYPE).itemsize
EOS_PREFIX = b"DRAVA_EOS:"
PUBLISH_CHUNK = 16

_next_start = 0
_published_frames = 0


def warmup_model(runs: int = 2, batch_size: int = DRAVA_INFER_BATCH) -> None:
    dummy = np.zeros((batch_size, PATCH_SIDE, PATCH_SIDE, 1), dtype=FRAME_DTYPE)
    for _ in range(runs):
        model.predict(dummy, verbose=0)
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Warmup done: runs={runs}, batch={batch_size}")


def func(frames) -> None:
    global _next_start, _published_frames
    batch_raw = []
    eos_raw = None
    expected_frames = None
    for raw in frames:
        if raw.startswith(EOS_PREFIX):
            eos_raw = raw
            try:
                expected_frames = int(raw[len(EOS_PREFIX):].decode("ascii"))
            except ValueError:
                raise ValueError(f"malformed EOS marker: {raw!r}")
            continue
        if len(raw) == 0:
            continue
        if len(raw) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")
        batch_raw.append(raw)
    if not batch_raw and eos_raw is not None:
        rc = drava.publish_py(eos_raw)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py(EOS) failed with rc={rc}")
        return
    if not batch_raw:
        return

    batch_size = len(batch_raw)
    start = _next_start
    end = start + batch_size
    _next_start = end
    expected_for_payload = expected_frames if expected_frames is not None else 0

    stacked = b"".join(batch_raw)
    tensor = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
        (batch_size, PATCH_SIDE, PATCH_SIDE, 1), order="C"
    )
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

    _published_frames += batch_size

    if eos_raw is not None:
        if expected_frames is None or _published_frames < expected_frames:
            raise RuntimeError(
                f"EOS forwarded before all frames were published: "
                f"published={_published_frames} expected={expected_frames}"
            )
        rc = drava.publish_py(eos_raw)
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
    drava.set_callback_batch(DRAVA_INFER_BATCH)
    drava.set_callback_serialize(1)
    drava.set_callback_flush_timeout_ms(0)
    drava.register_routine_py(func)
    rc = drava.listen_py()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
finally:
    rc = drava.deinit()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.deinit() failed with rc={rc}")
