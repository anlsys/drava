# Batch inference with a single callback.

import time
import os
import threading
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

DRAVA_INFER_BATCH = int(os.getenv("DRAVA_INFER_BATCH", "128"))
LOG_EVERY = DRAVA_INFER_BATCH
PATCH_SIDE = 64
FRAME_DTYPE = np.float32
FRAME_BYTES = PATCH_SIDE * PATCH_SIDE * 1 * np.dtype(FRAME_DTYPE).itemsize
EOS_PREFIX = b"DRAVA_EOS:"

_total_infers = 0
_t0 = None
_next_log = LOG_EVERY
_first_arrival_s = None
_last_done_s = None
_expected_frames = None
_state_lock = threading.Lock()
_final_logged = False


def warmup_model(runs=2, batch_size=DRAVA_INFER_BATCH):
    dummy = np.zeros((batch_size, PATCH_SIDE, PATCH_SIDE, 1), dtype=FRAME_DTYPE)
    for _ in range(runs):
        model.predict(dummy, verbose=0)
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Warmup done: runs={runs}, batch={batch_size}")


def func(frames):
    global _total_infers, _t0, _next_log
    global _first_arrival_s, _last_done_s
    global _final_logged, _expected_frames

    arrival_s = time.perf_counter()
    batch_raw = []
    info_line = None
    for raw in frames:
        if raw.startswith(EOS_PREFIX):
            try:
                eos_frames = int(raw[len(EOS_PREFIX):].decode("ascii"))
            except ValueError:
                drava.log(drava.DRAVA_VERBOSE_WARN, f"Ignoring malformed EOS marker: {raw!r}")
                continue
            with _state_lock:
                prev = _expected_frames
                if (_expected_frames is None) or (eos_frames > _expected_frames):
                    _expected_frames = eos_frames
                if prev != _expected_frames:
                    info_line = f"EOS received: expected_frames={_expected_frames}"
            continue
        if len(raw) == 0:
            # Backward-compatible fallback for older publishers.
            continue
        if len(raw) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")
        batch_raw.append(raw)

    log_line = None
    final_line = None

    if batch_raw:
        stacked = b"".join(batch_raw)
        tensor = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
            (len(batch_raw), PATCH_SIDE, PATCH_SIDE, 1), order="C"
        )

        t_inf0 = time.perf_counter()
        pred_amp, pred_phi = model.predict(tensor, verbose=0)
        t_inf1 = time.perf_counter()
        done_s = t_inf1
        step_s = (t_inf1 - t_inf0)
        step_ms = step_s * 1000.0

        with _state_lock:
            if _t0 is None:
                _t0 = t_inf0
                _first_arrival_s = arrival_s
            _last_done_s = done_s

            _total_infers += tensor.shape[0]
            wall_s = (t_inf1 - _t0)
            wall_avg_fps = (_total_infers / wall_s) if wall_s > 0 else float("inf")

            if _total_infers >= _next_log:
                log_line = (
                    f"[frames]={_total_infers} batch={tensor.shape[0]} step_ms={step_ms:.2f} "
                    f"wall_avg_fps={wall_avg_fps:.2f}"
                )
                _next_log += LOG_EVERY

    with _state_lock:
        if (
                (not _final_logged)
                and (_expected_frames is not None)
                and (_total_infers >= _expected_frames)
                and (_first_arrival_s is not None)
                and (_last_done_s is not None)
        ):
            app_e2e_s = (_last_done_s - _first_arrival_s)
            final_wall_avg_fps = (_total_infers / app_e2e_s) if app_e2e_s > 0 else float("inf")
            final_line = (
                f"[final] frames={_total_infers} "
                f"expected_frames={_expected_frames} "
                f"frame0_arrival_s={_first_arrival_s:.6f} "
                f"frame{_expected_frames}_done_s={_last_done_s:.6f} "
                f"end_to_end_latency_s={app_e2e_s:.6f} "
                f"final_wall_avg_fps={final_wall_avg_fps:.2f}"
            )
            _final_logged = True

    if info_line is not None:
        drava.log(drava.DRAVA_VERBOSE_INFO, info_line)
    if log_line is not None:
        drava.log(drava.DRAVA_VERBOSE_INFO, log_line)
    if final_line is not None:
        drava.log(drava.DRAVA_VERBOSE_INFO, final_line)

    return None


# -----------------------------
# Drava run loop
# -----------------------------
# Set transport via env var:
#   export DRAVA_TRANSPORT=nats   (or socket)
warmup_model()
drava.log(drava.DRAVA_VERBOSE_INFO, "Finalization mode: automatic (EOS marker with frame count)")

rc = drava.init()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(
        f"drava.init() failed with rc={rc}. "
        "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
    )

drava.register_routine_py(func)

rc = drava.listen_py()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(f"drava.listen_py() failed with rc={rc}")

rc = drava.deinit()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(f"drava.deinit() failed with rc={rc}")
