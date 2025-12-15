import drava
import json, base64
import numpy as np
import tensorflow as tf
from keras.models import load_model
from sklearn.metrics import mean_squared_error as mse
from skimage.transform import resize


# -----------------------------
# GPU config (optional)
# -----------------------------
def configure_gpu_memory_growth():
    gpus = tf.config.experimental.list_physical_devices("GPU")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            print(e)


# -----------------------------
# Stitching helpers (same logic)
# -----------------------------
def stitch_component(pred_patches_2d: np.ndarray,
                     tst_side: int = 60,
                     patch_size: int = 64,
                     point_size: int = 3) -> np.ndarray:
    """
    pred_patches_2d: (N,64,64) amplitude OR phase patches
    """
    overlap = 4 * point_size

    composite = np.zeros((tst_side * point_size + overlap,
                          tst_side * point_size + overlap), float)
    ctr = np.zeros_like(composite)

    data_reshaped = pred_patches_2d.reshape(
        tst_side, tst_side, patch_size, patch_size
    )[:, :, patch_size // 2 - overlap // 2: patch_size // 2 + overlap // 2,
    patch_size // 2 - overlap // 2: patch_size // 2 + overlap // 2]

    for i in range(tst_side):
        for j in range(tst_side):
            r0 = point_size * i
            c0 = point_size * j
            composite[r0:r0 + overlap, c0:c0 + overlap] += data_reshaped[i, j]
            ctr[r0:r0 + overlap, c0:c0 + overlap] += 1

    stitched = composite[overlap // 2:-overlap // 2,
    overlap // 2:-overlap // 2] / ctr[overlap // 2:-overlap // 2,
    overlap // 2:-overlap // 2]
    return stitched


def downsample_to_scan(stitched: np.ndarray, target_side: int = 60) -> np.ndarray:
    return resize(stitched, (target_side, target_side),
                  preserve_range=True, anti_aliasing=True)


# -----------------------------
# Global state for accumulation
# -----------------------------
DATA_DIR = "PtychoNN_data_partial"
WT_DIR = f"{DATA_DIR}/wts4"

configure_gpu_memory_growth()

min_epoch = int(np.load(f"{WT_DIR}/min_epoch.npy"))
MODEL_PATH = f"{WT_DIR}/weights.{min_epoch:02d}.hdf5"
print(f"Loading model: {MODEL_PATH}")
model = load_model(MODEL_PATH)
print("Model loaded.")

# Ground-truth is optional, but needed for MSE
Y_I_test = np.load(f"{DATA_DIR}/Y_I_test.npy")
Y_phi_test = np.load(f"{DATA_DIR}/Y_phi_test.npy")
nltest = int(Y_I_test.shape[0] ** 0.5)

amp_gt_center = Y_I_test.reshape(nltest, nltest, 64, 64)[:, :, 32, 32]
phi_gt_center = Y_phi_test.reshape(nltest, nltest, 64, 64)[:, :, 32, 32]

# These will be allocated once we know n_total
current_job_id = None
amp_pred_all = None  # (N,64,64)
phi_pred_all = None  # (N,64,64)
received_mask = None  # (N,)
tst_side = 60


def reset_job(job_id: int, n_total: int):
    global current_job_id, amp_pred_all, phi_pred_all, received_mask
    current_job_id = job_id
    amp_pred_all = np.empty((n_total, 64, 64), dtype=np.float32)
    phi_pred_all = np.empty((n_total, 64, 64), dtype=np.float32)
    received_mask = np.zeros((n_total,), dtype=bool)
    print(f"[accumulator] reset: job_id={job_id} n_total={n_total}")


def finalize_and_report():
    # stitch + downsample
    stitched_amp = stitch_component(amp_pred_all, tst_side=tst_side)
    stitched_phi = stitch_component(phi_pred_all, tst_side=tst_side)

    stitched_amp_down = downsample_to_scan(stitched_amp, target_side=tst_side)
    stitched_phi_down = downsample_to_scan(stitched_phi, target_side=tst_side)

    # MSE against GT centers
    amp_mse = mse(stitched_amp_down, amp_gt_center)
    phi_mse = mse(stitched_phi_down, phi_gt_center)

    print("====================================")
    print("All patches received. Final results:")
    print("MSE in amplitude:", amp_mse)
    print("MSE in phase:", phi_mse)
    print("====================================")


def func(s: str):
    global amp_pred_all, phi_pred_all, received_mask, current_job_id

    msg = json.loads(s)
    if msg.get("kind") != "ptychonn_batch":
        return

    job_id = int(msg["job_id"])
    start = int(msg["start"])
    end = int(msg["end"])
    n_total = int(msg["n_total"])

    patch_side = int(msg["patch_side"])
    dtype = np.dtype(msg["dtype"])
    order = msg.get("order", "C")

    # Reset accumulator if new job arrives
    if current_job_id != job_id:
        reset_job(job_id, n_total)

    # Decode payload -> (B,64,64,1)
    raw = base64.b64decode(msg["data_b64"])
    expected = (end - start) * patch_side * patch_side * 1 * dtype.itemsize
    if len(raw) != expected:
        raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {expected}")

    batch = np.frombuffer(raw, dtype=dtype).reshape((end - start, patch_side, patch_side, 1), order=order)

    # Inference
    pred_amp, pred_phi = model.predict(batch, verbose=0)  # each (B,64,64,1)

    # Store predictions by index (order-safe)
    amp_pred_all[start:end] = pred_amp[..., 0]
    phi_pred_all[start:end] = pred_phi[..., 0]
    received_mask[start:end] = True

    # Progress + finalize if complete
    got = int(received_mask.sum())
    total = received_mask.size
    if got % 256 == 0 or got == total:
        print(f"[accumulator] received {got}/{total}")

    if got == total:
        finalize_and_report()

drava.init("nats")
# drava.init("socket")
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
