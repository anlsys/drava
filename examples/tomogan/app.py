import threading
from pathlib import Path

import drava
import h5py
import numpy as np
import tensorflow as tf

from config import (
    DATASET_PATH,
    DRAVA_INFER_BATCH,
    FRAME_BYTES,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    MODEL_PATH,
    OUTPUT_PATH,
    PNG_DIR,
    SAVE_OUTPUT,
    TEST_INPUT_KEY,
    TEST_TARGET_KEY,
    save2img,
)


def configure_gpu_memory_growth() -> None:
    gpus = tf.config.experimental.list_physical_devices("GPU")
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Visible GPUs: {len(gpus)}, {gpus}")
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as exc:
            drava.log(drava.DRAVA_VERBOSE_ERROR, f"Error in configuring gpu: {exc}")


def load_model_or_raise():
    if not MODEL_PATH:
        raise RuntimeError(
            "Set DRAVA_TOMOGAN_MODEL_PATH (or TOMOGAN_MODEL_PATH) to a saved TomoGAN generator model."
        )
    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        raise RuntimeError(f"TomoGAN model path does not exist: {model_path}")
    model = tf.keras.models.load_model(model_path, compile=False)
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Loaded model: {model_path}")
    return model


def warmup_model(model, runs: int = 2, batch_size: int = DRAVA_INFER_BATCH) -> None:
    dummy = np.zeros((batch_size, FRAME_HEIGHT, FRAME_WIDTH, 1), dtype=np.float32)
    for _ in range(runs):
        model.predict(dummy, verbose=0)
    drava.log(
        drava.DRAVA_VERBOSE_INFO,
        f"Warmup done: runs={runs}, batch={batch_size}, frame=({FRAME_HEIGHT}, {FRAME_WIDTH})",
    )


def load_ground_truth(n_expected: int):
    if not DATASET_PATH.exists():
        drava.log(drava.DRAVA_VERBOSE_INFO, f"Dataset not found, skipping GT load: {DATASET_PATH}")
        return None
    with h5py.File(DATASET_PATH, "r") as h5fd:
        if TEST_TARGET_KEY not in h5fd:
            drava.log(
                drava.DRAVA_VERBOSE_INFO,
                f"Dataset key {TEST_TARGET_KEY!r} not found, skipping GT load",
            )
            return None
        gt = h5fd[TEST_TARGET_KEY][:]
    if gt.ndim != 3:
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"Ground-truth dataset has unexpected shape {gt.shape}, skipping GT metrics",
        )
        return None
    return gt[:n_expected].astype(np.float32)


def write_output(chunks, n_expected: int) -> None:
    if not chunks:
        raise RuntimeError("No inference results were collected before finalization")

    chunks = sorted(chunks, key=lambda item: item[0])
    noisy = np.concatenate([chunk[1] for chunk in chunks], axis=0)
    denoised = np.concatenate([chunk[2] for chunk in chunks], axis=0)

    if noisy.shape[0] != denoised.shape[0]:
        raise RuntimeError(
            f"input/output frame mismatch: noisy={noisy.shape[0]}, denoised={denoised.shape[0]}"
        )
    if n_expected and noisy.shape[0] != n_expected:
        raise RuntimeError(
            f"received {noisy.shape[0]} frames but EOS declared {n_expected}"
        )

    gt = load_ground_truth(noisy.shape[0])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(OUTPUT_PATH, "w") as h5fd:
        h5fd.create_dataset("ns", data=noisy, dtype=np.float32)
        h5fd.create_dataset("dn", data=denoised, dtype=np.float32)
        if gt is not None:
            h5fd.create_dataset("gt", data=gt, dtype=np.float32)

    saved_paths = [str(OUTPUT_PATH)]
    if noisy.shape[0] > 0:
        save_idx = noisy.shape[0] - 1
        PNG_DIR.mkdir(parents=True, exist_ok=True)
        ns_png = PNG_DIR / "ns.png"
        dn_png = PNG_DIR / "it00500.png"
        save2img(noisy[save_idx], ns_png)
        save2img(denoised[save_idx], dn_png)
        saved_paths.extend([str(ns_png), str(dn_png)])
        if gt is not None and gt.shape[0] > 0:
            gt_png = PNG_DIR / "gt.png"
            err_png = PNG_DIR / "abs_err_dn_vs_gt.png"
            save2img(gt[save_idx], gt_png)
            save2img(np.abs(denoised[save_idx] - gt[save_idx]), err_png)
            saved_paths.extend([str(gt_png), str(err_png)])

    if gt is not None and gt.shape == denoised.shape:
        mse_noisy = float(np.mean((noisy - gt) ** 2))
        mse_denoised = float(np.mean((denoised - gt) ** 2))
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"Wrote {OUTPUT_PATH} with {denoised.shape[0]} frames; "
            f"MSE noisy={mse_noisy:.6f}, denoised={mse_denoised:.6f}; "
            f"saved_files={saved_paths}",
        )
    else:
        drava.log(
            drava.DRAVA_VERBOSE_INFO,
            f"Wrote {OUTPUT_PATH} with {denoised.shape[0]} frames; saved_files={saved_paths}",
        )


def finalize_without_output(n_expected: int, processed_frames: int) -> None:
    if n_expected and processed_frames != n_expected:
        raise RuntimeError(
            f"received {processed_frames} frames but EOS declared {n_expected}"
        )
    drava.log(
        drava.DRAVA_VERBOSE_INFO,
        f"Benchmark finalize without output: processed_frames={processed_frames}",
    )


configure_gpu_memory_growth()
drava.log(drava.DRAVA_VERBOSE_INFO, f"Built with CUDA: {tf.test.is_built_with_cuda()}")
MODEL = load_model_or_raise()
warmup_model(MODEL)

EOS_PREFIX = b"DRAVA_EOS:"
_state_lock = threading.Lock()
_next_start = 0
_processed_frames = 0
_expected_frames = None
_eos_seen = False
_finalized = False
_chunks = []


def _mark_eos(expected_frames):
    global _expected_frames, _eos_seen
    with _state_lock:
        _eos_seen = True
        if expected_frames is not None:
            if _expected_frames is None or expected_frames > _expected_frames:
                _expected_frames = expected_frames


def _maybe_finalize():
    global _finalized
    with _state_lock:
        if _finalized:
            return
        if not _eos_seen or _expected_frames is None or _processed_frames < _expected_frames:
            return
        _finalized = True
        chunks = list(_chunks)
        processed_frames = int(_processed_frames)
        n_expected = int(_expected_frames)
    if SAVE_OUTPUT:
        write_output(chunks, n_expected)
    else:
        finalize_without_output(n_expected, processed_frames)


def func(frames) -> None:
    global _next_start, _processed_frames
    batch_raw = []
    eos_expected = None

    for raw in frames:
        if raw.startswith(EOS_PREFIX):
            try:
                eos_expected = int(raw[len(EOS_PREFIX):].decode("ascii"))
            except ValueError as exc:
                raise ValueError(f"malformed EOS marker: {raw!r}") from exc
            continue
        if len(raw) == 0:
            continue
        if len(raw) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")
        batch_raw.append(raw)

    if eos_expected is not None:
        _mark_eos(eos_expected)

    if not batch_raw:
        _maybe_finalize()
        return

    batch_size = len(batch_raw)
    with _state_lock:
        start = _next_start
        _next_start += batch_size

    tensor = np.frombuffer(b"".join(batch_raw), dtype=np.float32).reshape(
        (batch_size, FRAME_HEIGHT, FRAME_WIDTH, 1),
        order="C",
    )
    pred = MODEL.predict(tensor, verbose=0).astype(np.float32)
    if pred.ndim != 4 or pred.shape[-1] != 1:
        raise RuntimeError(f"unexpected model output shape: {pred.shape}")

    with _state_lock:
        if SAVE_OUTPUT:
            noisy = tensor[..., 0].copy()
            denoised = pred[..., 0].copy()
            _chunks.append((start, noisy, denoised))
        _processed_frames += batch_size

    _maybe_finalize()


rc = drava.init()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(
        f"drava.init() failed with rc={rc}. "
        "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
    )

try:
    drava.set_callback_batch(DRAVA_INFER_BATCH)
    drava.set_callback_serialize(0)
    drava.set_callback_flush_timeout_ms(0)
    drava.register_routine_py(func)
    rc = drava.listen_py()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
finally:
    rc = drava.deinit()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.deinit() failed with rc={rc}")
