# Batched inference (buffer frames, predict in batches)

import time
import drava
import json, base64
import numpy as np
import tensorflow as tf
from keras.models import load_model

def configure_gpu_memory_growth():
    gpus = tf.config.experimental.list_physical_devices("GPU")
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Visible GPUs: {len(gpus)}, {gpus}")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            drava.log(drava.DRAVA_VERBOSE_ERROR, f"Error in configuring gpu: {str(e)}")

DATA_DIR = "PtychoNN_data_partial"
WT_DIR = f"{DATA_DIR}/wts4"

configure_gpu_memory_growth()
drava.log(drava.DRAVA_VERBOSE_INFO, f"Built with CUDA: {tf.test.is_built_with_cuda()}")

min_epoch = int(np.load(f"{WT_DIR}/min_epoch.npy"))
MODEL_PATH = f"{WT_DIR}/weights.{min_epoch:02d}.hdf5"
model = load_model(MODEL_PATH)
drava.log(drava.DRAVA_VERBOSE_INFO, f"Loaded model: {MODEL_PATH}")

BATCH_SIZE = 32
LOG_EVERY_FRAMES = 256

_total_frames = 0
_t0 = None
current_job_id = None

_batch_frames = []       # list of (64,64,1) arrays
_batch_idxs = []         # optional: keep idxs for debug/logging
_batch_total_frames = 0  # expected total for current job (from payload)

def _flush_batch(reason: str):
    global _batch_frames, _batch_idxs, _total_frames, _t0

    if not _batch_frames:
        return

    # Stack to (B,64,64,1)
    batch = np.stack(_batch_frames, axis=0)

    t0 = time.perf_counter()
    pred_amp, pred_phi = model.predict(batch, verbose=0)
    t1 = time.perf_counter()

    bsz = batch.shape[0]
    _total_frames += bsz

    elapsed = t1 - _t0 if _t0 is not None else 0.0
    avg_fps = (_total_frames / elapsed) if elapsed > 0 else float("inf")
    batch_ms = (t1 - t0) * 1000.0
    per_frame_ms = batch_ms / bsz

    last_idx = _batch_idxs[-1] if _batch_idxs else -1

    if (_total_frames % LOG_EVERY_FRAMES) < bsz or reason in ("job_switch", "job_end"):
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"[batch] reason={reason} bsz={bsz} last_idx={last_idx} "
            f"batch_ms={batch_ms:.2f} per_frame_ms={per_frame_ms:.2f} "
            f"avg_fps={avg_fps:.2f}"
        )

    _batch_frames.clear()
    _batch_idxs.clear()

def func(s: str):
    global _total_frames, _t0, current_job_id, _batch_total_frames

    msg = json.loads(s)
    if msg.get("kind") != "ptychonn_frame":
        return

    job_id = int(msg.get("job_id", -1))
    idx = int(msg.get("idx", -1))
    total_frames = int(msg.get("n_total", 0))

    # Start/restart job stats when job changes
    if current_job_id != job_id:
        if current_job_id is not None:
            _flush_batch("job_switch")

        current_job_id = job_id
        _total_frames = 0
        _batch_total_frames = total_frames
        _t0 = time.perf_counter()
        drava.log(drava.DRAVA_VERBOSE_INFO, f"[job] new job_id={job_id} start_t={_t0:.6f}")

    patch_side = int(msg["patch_side"])
    dtype = np.dtype(msg["dtype"])
    order = msg.get("order", "C")

    raw = base64.b64decode(msg["data_b64"])
    expected = patch_side * patch_side * 1 * dtype.itemsize
    if len(raw) != expected:
        raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {expected}")

    frame = np.frombuffer(raw, dtype=dtype).reshape((patch_side, patch_side, 1), order=order)

    _batch_frames.append(frame)
    _batch_idxs.append(idx)


    if len(_batch_frames) >= BATCH_SIZE:
        _flush_batch("full")

    if idx == total_frames - 1:
        _flush_batch("job_end")

drava.init()
drava.register_routine_py(func)
drava.listen_py()
drava.deinit()
