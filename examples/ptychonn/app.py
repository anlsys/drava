# Batch inference with a single callback.

import time
import drava
import numpy as np
import tensorflow as tf
from keras.models import load_model


# -----------------------------
# GPU config (optional)
# -----------------------------
def configure_gpu_memory_growth():
    gpus = tf.config.experimental.list_physical_devices("GPU")
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Visible GPUs: {len(gpus)}, {gpus}")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            drava.log(drava.DRAVA_VERBOSE_ERROR, f"Error in configuring gpu: {str(e)}")


# -----------------------------
# Model load
# -----------------------------
DATA_DIR = "PtychoNN_data_partial"
WT_DIR = f"{DATA_DIR}/wts4"

configure_gpu_memory_growth()
drava.log(drava.DRAVA_VERBOSE_INFO, f"Built with CUDA: {tf.test.is_built_with_cuda()}")

min_epoch = int(np.load(f"{WT_DIR}/min_epoch.npy"))
MODEL_PATH = f"{WT_DIR}/weights.{min_epoch:02d}.hdf5"
model = load_model(MODEL_PATH)
drava.log(drava.DRAVA_VERBOSE_INFO, f"Loaded model: {MODEL_PATH}")


LOG_EVERY = 256
PATCH_SIDE = 64
FRAME_DTYPE = np.float32
FRAME_BYTES = PATCH_SIDE * PATCH_SIDE * 1 * np.dtype(FRAME_DTYPE).itemsize

_total_infers = 0
_t0 = None
_next_log = LOG_EVERY
def func(frames):
    global _total_infers, _t0, _next_log
    batch_raw = []
    for raw in frames:
        if len(raw) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")
        batch_raw.append(raw)

    if not batch_raw:
        return None

    stacked = b"".join(batch_raw)
    tensor = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
        (len(batch_raw), PATCH_SIDE, PATCH_SIDE, 1), order="C"
    )

    if _t0 is None:
        _t0 = time.perf_counter()

    t_inf0 = time.perf_counter()
    pred_amp, pred_phi = model.predict(tensor, verbose=0)
    t_inf1 = time.perf_counter()

    _total_infers += tensor.shape[0]
    elapsed = t_inf1 - _t0
    avg_fps = (_total_infers / elapsed) if elapsed > 0 else float("inf")
    step_ms = (t_inf1 - t_inf0) * 1000.0

    if _total_infers >= _next_log:
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"[frames]={_total_infers} batch={tensor.shape[0]} step_ms={step_ms:.2f} avg_fps={avg_fps:.2f}",
        )
        _next_log += LOG_EVERY

    return None


# -----------------------------
# Drava run loop
# -----------------------------
# Set transport via env var:
#   export DRAVA_TRANSPORT=nats   (or socket)
drava.init()
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
