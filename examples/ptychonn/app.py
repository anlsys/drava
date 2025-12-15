import drava
import json, base64
import numpy as np
import tensorflow as tf
from keras.models import load_model

# Optional: GPU config
gpus = tf.config.experimental.list_physical_devices("GPU")
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)

DATA_DIR = "PtychoNN_data_partial"

# ---- Load PtychoNN model once at import time ----
min_epoch = int(np.load(f"{DATA_DIR}/min_epoch.npy"))
MODEL_PATH = f"{DATA_DIR}/weights.66.hdf5"

print(f"Loading PtychoNN model from: {MODEL_PATH}")
model = load_model(MODEL_PATH)
print("Model loaded.")


def func(s: str):
    """
    Drava callback.

    s is a JSON string with:
      rows, cols, dtype, order, frame_id, patch_side, data_b64
    representing a batch of flattened diffraction patches.
    """
    msg = json.loads(s)
    rows = int(msg["rows"])
    cols = int(msg["cols"])
    dtype = np.dtype(msg["dtype"])
    order = msg.get("order", "C")
    patch_side = int(msg["patch_side"])
    frame_id = msg.get("frame_id")

    # Decode base64 → bytes
    raw = base64.b64decode(msg["data_b64"])
    expected_bytes = rows * cols * dtype.itemsize
    if len(raw) != expected_bytes:
        raise ValueError(
            f"payload size mismatch: got {len(raw)} bytes, expected {expected_bytes}"
        )

    # Bytes → flat 2D array (rows, cols)
    arr_flat = np.frombuffer(raw, dtype=dtype)
    arr_2d = arr_flat.reshape((rows, cols), order=order)

    # 2D → 4D tensor for Keras: (batch, H, W, 1)
    arr_4d = arr_2d.reshape((rows, patch_side, patch_side, 1))

    print(
        f"Received batch frame_id={frame_id}, "
        f"arr_4d shape={arr_4d.shape}"
    )

    # ---- PtychoNN inference ----
    # pred_amp, pred_phi each shape (rows, patch_side, patch_side, 1)
    pred_amp, pred_phi = model.predict(arr_4d, verbose=0)

    # For demo: print simple statistics
    mean_amp = float(np.mean(pred_amp))
    mean_phi = float(np.mean(pred_phi))
    print(
        f"frame_id={frame_id} | "
        f"batch_size={rows} | "
        f"mean_amp={mean_amp:.4f}, mean_phi={mean_phi:.4f}"
    )


# initialization supports nats or socket
drava.init("nats")
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
