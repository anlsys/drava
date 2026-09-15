"""PtychoPINN stage 1: object-patch inference.

Each incoming frame is one *group* of C overlapping diffraction patterns
(C x N x N float32, row-major), assembled offline by prepare_dataset.py. The
callback runs the published autoencoder over the batch and publishes the centre
crop of the predicted complex object patches downstream, where stage 2 splats
them onto the reconstruction canvas.

Note on the model call: ``forward_predict(x, positions, probe, input_scale_factor)``
uses only ``x`` and ``input_scale_factor`` -- it is just
``scale -> autoencoder -> amp * exp(i*phase)``. ``positions`` and ``probe`` are
accepted purely for signature compatibility with the training ``forward()``,
where the physics forward model consumes them. Passing ``None`` here avoids
allocating a multi-megabyte dummy probe per batch.
"""
import json

import drava
import numpy as np
import torch

from config import (
    DRAVA_INFER_BATCH,
    META_FILE,
    MLRUNS_DIR,
    RUN_ID,
    STAGE1_JOB_ID,
    TORCH_DEVICE,
    USE_MIXED_PRECISION,
)
from pipeline_schema import encode_stage1_patches

# --------------------------------------------------------------------------- #
# Geometry comes from the prep artifact, which derived it from the model's own
# MLflow config. Never guess it here.
# --------------------------------------------------------------------------- #
if not META_FILE.is_file():
    raise RuntimeError(
        f"Missing prep metadata: {META_FILE}\n"
        "Run prepare_dataset.py before starting the pipeline."
    )
META = json.loads(META_FILE.read_text(encoding="utf-8"))

PATCH_SIDE = int(META["N"])
GROUP_SIZE = int(META["C"])
MIDDLE_TRIM = int(META["middle_trim"])
RMS_SCALE = float(META["rms_scaling_constant"])
N_GROUPS = int(META["n_groups"])

FRAME_DTYPE = np.float32
FRAME_BYTES = GROUP_SIZE * PATCH_SIDE * PATCH_SIDE * np.dtype(FRAME_DTYPE).itemsize
if FRAME_BYTES != int(META["frame_bytes"]):
    raise RuntimeError(
        f"frame size disagreement: computed {FRAME_BYTES}, meta says {META['frame_bytes']}"
    )

# Keep each downstream message well under the NATS max_payload (8MB in nats.conf).
PUBLISH_CHUNK = 64

_CENTER_START = PATCH_SIDE // 2 - MIDDLE_TRIM // 2
_CENTER_END = PATCH_SIDE // 2 + MIDDLE_TRIM // 2


def resolve_device() -> torch.device:
    """Resolve the inference device, failing loudly rather than downgrading.

    A silent CPU fallback would also disable FP16 autocast and make any timing
    or energy measurement meaningless, so a misconfigured job should stop here.
    """
    if TORCH_DEVICE.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            f"PTYCHOPINN_DEVICE={TORCH_DEVICE!r} but torch.cuda.is_available() is False. "
            "Set PTYCHOPINN_DEVICE=cpu explicitly if you really want CPU."
        )
    return torch.device(TORCH_DEVICE)


def resolve_local_model_path(run_id: str, mlruns_dir) -> str | None:
    """Find ``<mlruns>/<experiment>/<run_id>/artifacts/model`` on disk.

    The ``runs:/`` URI depends on absolute paths baked into each run's
    ``meta.yaml``. Those go stale whenever the mlruns tree is moved, which is
    exactly what happens when the Zenodo tarball is unpacked somewhere new.
    """
    for candidate in sorted(mlruns_dir.glob(f"*/{run_id}/artifacts/model")):
        if (candidate / "MLmodel").exists():
            return str(candidate)
    return None


def load_model(device: torch.device):
    import mlflow

    if not RUN_ID:
        raise RuntimeError(
            "No MLflow run id. Set PTYCHOPINN_MODEL to a known key or "
            "PTYCHOPINN_RUN_ID to an explicit hash."
        )
    tracking_uri = f"file:{MLRUNS_DIR.resolve()}"
    mlflow.set_tracking_uri(tracking_uri)
    model_uri = f"runs:/{RUN_ID}/model"
    drava.log(drava.DRAVA_VERBOSE_INFO, f"tracking_uri={tracking_uri}")

    try:
        model = mlflow.pytorch.load_model(model_uri, map_location=device)
    except Exception as exc:
        local_path = resolve_local_model_path(RUN_ID, MLRUNS_DIR.resolve())
        if local_path is None:
            raise
        drava.log(
            drava.DRAVA_VERBOSE_WARN,
            f"runs:/ URI failed ({exc}); loading local artifact {local_path}",
        )
        model = mlflow.pytorch.load_model(local_path, map_location=device)

    model.to(device)
    # Upstream sets this attribute directly (inference.py, analysis.py) rather
    # than calling .eval()/.train(); replicated verbatim so the reconstruction
    # matches the published one. With batch_norm disabled in the published
    # config this has no effect on the result.
    model.training = True
    return model


DEVICE = resolve_device()
drava.log(drava.DRAVA_VERBOSE_INFO, f"torch={torch.__version__} device={DEVICE}")
if DEVICE.type == "cuda":
    drava.log(
        drava.DRAVA_VERBOSE_INFO,
        f"cuda devices={torch.cuda.device_count()} name={torch.cuda.get_device_name(0)}",
    )

model = load_model(DEVICE)
drava.log(
    drava.DRAVA_VERBOSE_INFO,
    f"Loaded model: run_id={RUN_ID} dataset={META['dataset']} model={META['model_key']}",
)
drava.log(
    drava.DRAVA_VERBOSE_INFO,
    f"N={PATCH_SIDE} C={GROUP_SIZE} middle_trim={MIDDLE_TRIM} "
    f"groups={N_GROUPS} rms_scale={RMS_SCALE!r} amp={USE_MIXED_PRECISION}",
)

_AUTOCAST = USE_MIXED_PRECISION and DEVICE.type == "cuda"


def _infer(tensor: torch.Tensor) -> torch.Tensor:
    """Run forward_predict and return the centre crop, on CPU as complex64."""
    n = tensor.shape[0]
    in_scale = torch.full(
        (n, 1, 1, 1), RMS_SCALE, dtype=torch.float32, device=DEVICE
    )
    with torch.no_grad():
        if _AUTOCAST:
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                out = model.forward_predict(tensor, None, None, in_scale)
        else:
            out = model.forward_predict(tensor, None, None, in_scale)

    out = out[:, :, _CENTER_START:_CENTER_END, _CENTER_START:_CENTER_END]
    return out.to(torch.complex64).cpu()


def warmup_model(runs: int = 2, batch_size: int = DRAVA_INFER_BATCH) -> None:
    dummy = torch.zeros(
        (batch_size, GROUP_SIZE, PATCH_SIDE, PATCH_SIDE),
        dtype=torch.float32,
        device=DEVICE,
    )
    for _ in range(runs):
        _infer(dummy)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
    drava.log(drava.DRAVA_VERBOSE_INFO, f"Warmup done: runs={runs}, batch={batch_size}")


def func(frames, base_index) -> None:
    """Infer on a batch of scan-position groups and publish object patches.

    The runtime strips the EOS marker and forwards it downstream automatically
    (egress.forward_eos in pipeline.yaml), and supplies base_index -- the global
    index of the first group in this batch -- so the callback stays stateless
    and stage 2 can reassemble in any order.
    """
    for raw in frames:
        if len(raw) != FRAME_BYTES:
            raise ValueError(
                f"payload mismatch: got {len(raw)} bytes, expected {FRAME_BYTES}"
            )

    n = len(frames)
    stacked = b"".join(frames)
    array = np.frombuffer(stacked, dtype=FRAME_DTYPE).reshape(
        (n, GROUP_SIZE, PATCH_SIDE, PATCH_SIDE), order="C"
    )
    tensor = torch.from_numpy(np.ascontiguousarray(array)).to(DEVICE, non_blocking=True)

    patches = _infer(tensor).numpy()

    for off in range(0, n, PUBLISH_CHUNK):
        end = min(off + PUBLISH_CHUNK, n)
        payload = encode_stage1_patches(
            job_id=STAGE1_JOB_ID,
            start=base_index + off,
            end=base_index + end,
            n_total=N_GROUPS,
            patches=patches[off:end],
        )
        rc = drava.publish_py(payload)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py() failed with rc={rc}")


warmup_model()
drava.run(func)
