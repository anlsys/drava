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
PUBLISH_CHUNK = 16


def warmup_model(runs: int = 2, batch_size: int = DRAVA_INFER_BATCH) -> None:
    dummy = np.zeros((batch_size, PATCH_SIDE, PATCH_SIDE, 1), dtype=FRAME_DTYPE)
    for _ in range(runs):
        model.predict(dummy, verbose=0)
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Warmup done: runs={runs}, batch={batch_size}")


def func(frames, base_index) -> None:
    """Infer on a batch of raw diffraction patches and publish predictions.

    The runtime strips the EOS marker and forwards it downstream automatically
    (egress.forward_eos in pipeline.yaml), and supplies base_index — the global
    position of the first frame in this batch — so no shared counter is needed.
    """
    for raw in frames:
        if len(raw) != FRAME_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}")

    n = len(frames)
    stacked = b"".join(frames)
    tensor = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
        (n, PATCH_SIDE, PATCH_SIDE, 1), order="C"
    )
    pred_amp, pred_phi = model.predict(tensor, verbose=0)
    pred_amp_3d = pred_amp[..., 0]
    pred_phi_3d = pred_phi[..., 0]

    for off in range(0, n, PUBLISH_CHUNK):
        end = min(off + PUBLISH_CHUNK, n)
        payload = encode_stage1_prediction(
            job_id=STAGE1_JOB_ID,
            start=base_index + off,
            end=base_index + end,
            n_total=0,
            pred_amp=pred_amp_3d[off:end],
            pred_phi=pred_phi_3d[off:end],
        )
        rc = drava.publish_py(payload)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py() failed with rc={rc}")


warmup_model()
drava.run(func)
