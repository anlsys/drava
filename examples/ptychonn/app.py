# Single-frame inference (with avg inference rate)

import time
import drava
import json, base64
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

_total_infers = 0
_t0 = None
current_job_id = None

def func(s: str):
    global _total_infers, _t0, current_job_id

    msg = json.loads(s)
    if msg.get("kind") != "ptychonn_frame":
        return

    job_id = int(msg.get("job_id", -1))
    idx = int(msg.get("idx", -1))
    total_frames = int(msg.get("n_total", 0))

    # Reset stats when a new publisher run (new job_id) starts
    if current_job_id != job_id:
        current_job_id = job_id
        _total_infers = 0
        _t0 = time.perf_counter()
        drava.log(drava.DRAVA_VERBOSE_INFO, f"[job] new job_id={job_id} start_t={_t0:.6f}")

    patch_side = int(msg["patch_side"])
    dtype = np.dtype(msg["dtype"])
    order = msg.get("order", "C")

    raw = base64.b64decode(msg["data_b64"])
    expected = patch_side * patch_side * 1 * dtype.itemsize
    if len(raw) != expected:
        raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {expected}")

    frame = np.frombuffer(raw, dtype=dtype).reshape((1, patch_side, patch_side, 1), order=order)

    # ---- inference ----
    t_inf0 = time.perf_counter()
    pred_amp, pred_phi = model.predict(frame, verbose=0)
    t_inf1 = time.perf_counter()

    _total_infers += 1

    elapsed = t_inf1 - _t0
    avg_fps = (_total_infers / elapsed) if elapsed > 0 else float("inf")
    inf_ms = (t_inf1 - t_inf0) * 1000.0
    # drava.log(drava.DRAVA_VERBOSE_INFO,
    #           f"Infer: [frame]={_total_infers}/{total_frames} "
    #           f"[idx]={idx} "
    #           f"step_ms={inf_ms:.2f}")

    if _total_infers % LOG_EVERY == 0 or idx == total_frames - 1:
        drava.log(drava.DRAVA_VERBOSE_INFO,
                  f"[frame]={_total_infers}/{total_frames} "
                  f"[idx]={idx} "
                  f"step_ms={inf_ms:.2f} "
                  f"avg_fps={avg_fps:.2f}")


# -----------------------------
# Drava run loop
# -----------------------------
# Set transport via env var:
#   export DRAVA_TRANSPORT=nats   (or socket)
drava.init()
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()