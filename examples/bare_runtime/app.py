import os
import threading

import drava


EOS_PREFIX = b"DRAVA_EOS:"

PAYLOAD_BYTES = int(os.getenv("DRAVA_BARE_PAYLOAD_BYTES", "1"))
OUTPUT_PAYLOAD_BYTES = int(os.getenv("DRAVA_BARE_OUTPUT_PAYLOAD_BYTES", str(PAYLOAD_BYTES)))
GPU_BACKEND = os.getenv("DRAVA_BARE_GPU_BACKEND", "auto").lower()
KERNEL_LAUNCHES = int(os.getenv("DRAVA_BARE_KERNEL_LAUNCHES", "1"))
KERNEL_BLOCKS = int(os.getenv("DRAVA_BARE_KERNEL_BLOCKS", "1"))
KERNEL_THREADS = int(os.getenv("DRAVA_BARE_KERNEL_THREADS", "1"))
GPU_SYNC = os.getenv("DRAVA_BARE_GPU_SYNC", "1") not in ("0", "false", "False")
PUBLISH_MODE = os.getenv("DRAVA_BARE_PUBLISH_MODE", "none").lower()
CALLBACK_BATCH = int(os.getenv("DRAVA_CALLBACK_BATCH", "0"))
CALLBACK_FLUSH_TIMEOUT_MS = int(os.getenv("DRAVA_CALLBACK_FLUSH_TIMEOUT_MS", "0"))
CALLBACK_SERIALIZE = os.getenv("DRAVA_CALLBACK_SERIALIZE", "")

if PAYLOAD_BYTES <= 0:
    raise RuntimeError("DRAVA_BARE_PAYLOAD_BYTES must be positive")
if OUTPUT_PAYLOAD_BYTES <= 0:
    raise RuntimeError("DRAVA_BARE_OUTPUT_PAYLOAD_BYTES must be positive")
if KERNEL_LAUNCHES < 0:
    raise RuntimeError("DRAVA_BARE_KERNEL_LAUNCHES must be non-negative")
if PUBLISH_MODE not in ("none", "one_per_callback", "one_per_frame"):
    raise RuntimeError("DRAVA_BARE_PUBLISH_MODE must be none, one_per_callback, or one_per_frame")


class KernelRunner:
    def __init__(self, backend: str):
        self.backend = "none"
        self._kernel = None
        self._torch_tensor = None
        if backend in ("auto", "cupy"):
            if self._init_cupy():
                return
            if backend == "cupy":
                raise RuntimeError("DRAVA_BARE_GPU_BACKEND=cupy requested, but CuPy is unavailable")
        if backend in ("auto", "torch"):
            if self._init_torch():
                return
            if backend == "torch":
                raise RuntimeError("DRAVA_BARE_GPU_BACKEND=torch requested, but CUDA Torch is unavailable")
        if backend not in ("auto", "none"):
            raise RuntimeError(f"unknown DRAVA_BARE_GPU_BACKEND={backend!r}")

    def _init_cupy(self) -> bool:
        try:
            import cupy as cp
        except Exception:
            return False
        self._cp = cp
        self._kernel = cp.RawKernel(
            'extern "C" __global__ void drava_bare_noop() { }',
            "drava_bare_noop",
        )
        self.backend = "cupy"
        return True

    def _init_torch(self) -> bool:
        try:
            import torch
        except Exception:
            return False
        if not torch.cuda.is_available():
            return False
        self._torch = torch
        self._torch_tensor = torch.empty(1, device="cuda")
        self.backend = "torch"
        return True

    def run(self) -> None:
        if KERNEL_LAUNCHES == 0 or self.backend == "none":
            return
        if self.backend == "cupy":
            for _ in range(KERNEL_LAUNCHES):
                self._kernel((KERNEL_BLOCKS,), (KERNEL_THREADS,), ())
            if GPU_SYNC:
                self._cp.cuda.Stream.null.synchronize()
            return
        if self.backend == "torch":
            for _ in range(KERNEL_LAUNCHES):
                self._torch_tensor.add_(0.0)
            if GPU_SYNC:
                self._torch.cuda.synchronize()


kernel_runner = KernelRunner(GPU_BACKEND)
output_payload = b"\1" * OUTPUT_PAYLOAD_BYTES

_state_lock = threading.Lock()
_processed_frames = 0
_expected_frames = None
_eos_seen = False
_final_logged = False


def _mark_eos(expected_frames):
    global _expected_frames, _eos_seen
    with _state_lock:
        _eos_seen = True
        if expected_frames is not None:
            if _expected_frames is None or expected_frames > _expected_frames:
                _expected_frames = expected_frames


def _maybe_log_final():
    global _final_logged
    with _state_lock:
        if _final_logged:
            return
        if not _eos_seen or _expected_frames is None or _processed_frames < _expected_frames:
            return
        _final_logged = True
        processed = _processed_frames
        expected = _expected_frames
    drava.log(
        drava.DRAVA_VERBOSE_INFO,
        f"[bare-final] frames={processed} expected_frames={expected} "
        f"backend={kernel_runner.backend} publish_mode={PUBLISH_MODE}",
    )


def _publish_outputs(n_frames: int) -> None:
    if PUBLISH_MODE == "none" or n_frames <= 0:
        return
    if PUBLISH_MODE == "one_per_callback":
        rc = drava.publish_py(output_payload)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py() failed with rc={rc}")
        return
    for _ in range(n_frames):
        rc = drava.publish_py(output_payload)
        if rc != drava.DRAVA_SUCCESS:
            raise RuntimeError(f"drava.publish_py() failed with rc={rc}")


def func(frames) -> None:
    global _processed_frames
    n_data = 0
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
        if len(raw) != PAYLOAD_BYTES:
            raise ValueError(f"payload mismatch: got {len(raw)} bytes, expected {PAYLOAD_BYTES}")
        n_data += 1

    if eos_expected is not None:
        _mark_eos(eos_expected)

    if n_data:
        kernel_runner.run()
        _publish_outputs(n_data)
        with _state_lock:
            _processed_frames += n_data

    _maybe_log_final()


for _ in range(max(1, int(os.getenv("DRAVA_BARE_WARMUP_RUNS", "3")))):
    kernel_runner.run()

drava.log(
    drava.DRAVA_VERBOSE_INFO,
    f"[bare-runtime] backend={kernel_runner.backend} requested_backend={GPU_BACKEND} "
    f"payload_bytes={PAYLOAD_BYTES} kernel_launches={KERNEL_LAUNCHES} "
    f"publish_mode={PUBLISH_MODE}",
)

rc = drava.init()
if rc != drava.DRAVA_SUCCESS:
    raise RuntimeError(
        f"drava.init() failed with rc={rc}. "
        "If DRAVA_TRANSPORT=nats, rebuild Drava with NATS enabled."
    )

try:
    if CALLBACK_BATCH > 0:
        drava.set_callback_batch(CALLBACK_BATCH)
    drava.set_callback_flush_timeout_ms(CALLBACK_FLUSH_TIMEOUT_MS)
    if CALLBACK_SERIALIZE:
        drava.set_callback_serialize(0 if CALLBACK_SERIALIZE in ("0", "false", "False") else 1)
    drava.register_routine_py(func)
    rc = drava.listen_py()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.listen_py() failed with rc={rc}")
finally:
    rc = drava.deinit()
    if rc != drava.DRAVA_SUCCESS:
        raise RuntimeError(f"drava.deinit() failed with rc={rc}")
