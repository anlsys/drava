import time
import threading

import drava
import numpy as np
import tensorflow as tf
from keras.models import load_model

from config import (
    DATA_DIR,
    DRAVA_INFER_BATCH,
    LOG_EVERY,
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

_next_start = 0
_total_infers = 0
_infer_t0: float | None = None
_first_arrival_s: float | None = None
_last_done_s: float | None = None
_next_log = LOG_EVERY
_final_logged = False
_expected_frames: int | None = None
_published_frames = 0
_published_msgs = 0
_publish_t0: float | None = None
_state_lock = threading.Lock()
_predict_lock = threading.Lock()


def warmup_model(runs: int = 2, batch_size: int = DRAVA_INFER_BATCH) -> None:
    dummy = np.zeros((batch_size, PATCH_SIDE, PATCH_SIDE, 1), dtype=FRAME_DTYPE)
    for _ in range(runs):
        model.predict(dummy, verbose=0)
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Warmup done: runs={runs}, batch={batch_size}")


def func(frames) -> None:
    global _next_start, _total_infers, _infer_t0
    global _first_arrival_s, _last_done_s, _next_log, _final_logged
    global _published_frames, _published_msgs, _publish_t0, _expected_frames

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
            rc = drava.publish_py(raw)
            if rc != drava.DRAVA_SUCCESS:
                raise RuntimeError(f"drava.publish_py(EOS) failed with rc={rc}")
            with _state_lock:
                prev = _expected_frames
                if (_expected_frames is None) or (eos_frames > _expected_frames):
                    _expected_frames = eos_frames
                if prev != _expected_frames:
                    info_line = f"EOS received: expected_frames={_expected_frames}"
            continue
        if len(raw) == 0:
            continue
        if len(raw) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")
        batch_raw.append(raw)
    if info_line is not None:
        drava.log(drava.DRAVA_VERBOSE_INFO, info_line)

    log_line = None
    final_line = None

    if batch_raw:
        batch_size = len(batch_raw)
        stacked = b"".join(batch_raw)
        tensor = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
            (batch_size, PATCH_SIDE, PATCH_SIDE, 1), order="C"
        )

        t_inf0 = time.perf_counter()
        with _predict_lock:
            pred_amp, pred_phi = model.predict(tensor, verbose=0)
        t_inf1 = time.perf_counter()

        with _state_lock:
            start = _next_start
            end = start + batch_size
            _next_start = end
            expected_for_payload = _expected_frames if _expected_frames is not None else 0

        payload = encode_stage1_prediction(
            job_id=STAGE1_JOB_ID,
            start=start,
            end=end,
            n_total=expected_for_payload,
            pred_amp=pred_amp[..., 0],
            pred_phi=pred_phi[..., 0],
        )

        rc = drava.publish_py(payload)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py() failed with rc={rc}")

        with _state_lock:
            if _publish_t0 is None:
                _publish_t0 = time.perf_counter()
            _published_frames += batch_size
            _published_msgs += 1

            if _infer_t0 is None:
                _infer_t0 = t_inf0
                _first_arrival_s = arrival_s
            _last_done_s = t_inf1
            _total_infers += batch_size

            infer_wall_s = t_inf1 - _infer_t0
            infer_avg_fps = (_total_infers / infer_wall_s) if infer_wall_s > 0 else float("inf")
            publish_wall_s = (time.perf_counter() - _publish_t0) if _publish_t0 is not None else 0.0
            publish_avg_fps = (_published_frames / publish_wall_s) if publish_wall_s > 0 else 0.0
            step_ms = (t_inf1 - t_inf0) * 1000.0

            if _total_infers >= _next_log:
                log_line = (
                    f"[stage1] frames={_total_infers} batch={batch_size} step_ms={step_ms:.2f} "
                    f"infer_avg_fps={infer_avg_fps:.2f} published_frames={_published_frames} "
                    f"published_msgs={_published_msgs} publish_avg_fps={publish_avg_fps:.2f}"
                )
                _next_log += LOG_EVERY

    with _state_lock:
        expected = _expected_frames
        if (
                (not _final_logged)
                and (expected is not None)
                and (_total_infers >= expected)
                and (_first_arrival_s is not None)
                and (_last_done_s is not None)
        ):
            app_e2e_s = _last_done_s - _first_arrival_s
            e2e_fps = (_total_infers / app_e2e_s) if app_e2e_s > 0 else float("inf")
            infer_elapsed = (_last_done_s - _infer_t0) if _infer_t0 is not None else 0.0
            infer_avg_final = (_total_infers / infer_elapsed) if infer_elapsed > 0 else float("inf")
            publish_elapsed = (time.perf_counter() - _publish_t0) if _publish_t0 is not None else 0.0
            publish_avg_final = (
                (_published_frames / publish_elapsed) if publish_elapsed > 0 else 0.0
            )
            final_line = (
                f"[stage1-final] frames={_total_infers} expected_frames={expected} "
                f"frame0_arrival_s={_first_arrival_s:.6f} "
                f"last_infer_done_s={_last_done_s:.6f} end_to_end_latency_s={app_e2e_s:.6f} "
                f"infer_avg_fps={infer_avg_final:.2f} "
                f"publish_avg_fps={publish_avg_final:.2f} "
                f"e2e_fps={e2e_fps:.2f}"
            )
            _final_logged = True

    if log_line is not None:
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            log_line,
        )
    if final_line is not None:
        drava.log(drava.DRAVA_VERBOSE_INFO, final_line)


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
