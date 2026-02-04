# Single-frame inference

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
    print(f"Total GPUs: {len(gpus)}")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            print(e)


# -----------------------------
# Model load
# -----------------------------
DATA_DIR = "PtychoNN_data_partial"
WT_DIR = f"{DATA_DIR}/wts4"

configure_gpu_memory_growth()

min_epoch = int(np.load(f"{WT_DIR}/min_epoch.npy"))
MODEL_PATH = f"{WT_DIR}/weights.{min_epoch:02d}.hdf5"
print(f"Loading model: {MODEL_PATH}")
model = load_model(MODEL_PATH)
print("Model loaded.")


# -----------------------------
# Drava callback
# -----------------------------
def func(s: str):
    """
    Expects publisher payload like:
      kind: "ptychonn_frame"
      idx: int
      patch_side: 64
      dtype: "float32"
      order: "C"
      data_b64: base64(frame_bytes) where frame shape is (64,64,1)
    """
    msg = json.loads(s)
    if msg.get("kind") != "ptychonn_frame":
        return

    idx = int(msg.get("idx", -1))
    patch_side = int(msg["patch_side"])
    dtype = np.dtype(msg["dtype"])
    order = msg.get("order", "C")

    # Decode single frame -> (1,64,64,1)
    raw = base64.b64decode(msg["data_b64"])
    expected = patch_side * patch_side * 1 * dtype.itemsize
    if len(raw) != expected:
        raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {expected}")

    frame = np.frombuffer(raw, dtype=dtype).reshape((1, patch_side, patch_side, 1), order=order)

    # Single-frame inference
    pred_amp, pred_phi = model.predict(frame, verbose=0)  # each: (1,64,64,1)
    amp_mean = float(pred_amp.mean())
    phi_mean = float(pred_phi.mean())
    print(f"[infer] idx={idx} amp_shape={pred_amp.shape} phi_shape={pred_phi.shape} "
          f"amp_mean={amp_mean:.6f} phi_mean={phi_mean:.6f}")


# -----------------------------
# Drava run loop
# -----------------------------
# Set transport via env var:
#   export DRAVA_TRANSPORT=nats   (or socket)
drava.init()
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
