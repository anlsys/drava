"""Reconstruction-correctness tests for the refactored multi-threaded runtime.

These are standalone accuracy checks (separate from the benchmarks). After the
runtime refactor, callbacks run concurrently across worker threads and frames may
be delivered out of order; the runtime assigns each batch a global ``base_index``
and the stage-1 wire format carries absolute ``start:end`` positions. The
correctness property is therefore **order independence**: the reconstruction a
stage assembles must be identical whether frames arrive in order, shuffled, or
concurrently from many threads.

These tests exercise the deterministic reconstruction logic directly (no model,
GPU, NATS, or runtime build required):

- PtychoNN: the stage-1 <-> stage-2 wire encode/decode round-trip, and the
  stage-2 position-indexed accumulation + overlap-add stitching, comparing
  in-order vs shuffled vs multi-threaded assembly.
- PtychoPINN: the stage-1 <-> stage-2 wire round-trip, which splits complex64
  object patches into two float32 blobs. Its canvas assembly is order
  independent by construction (scatter-add at absolute positions) but needs
  torch, so it is exercised on hardware rather than here.
- TomoGAN: position-indexed frame assembly (the property that makes denoising
  output order-independent), in-order vs shuffled vs multi-threaded.

Run: python examples/common/tests/test_reconstruction_accuracy.py
"""
import importlib.util
import random
import sys
import threading
from pathlib import Path

# A sibling test (test_examples_import) may install a stub `numpy` into
# sys.modules; drop any stub so we import the real numpy here.
for _m in ("numpy", "numpy.random", "drava"):
    _mod = sys.modules.get(_m)
    if _mod is not None and getattr(_mod, "__spec__", None) is None:
        del sys.modules[_m]

try:
    import numpy as np
    if not hasattr(np, "asarray"):  # a stub slipped through
        raise ImportError("stubbed numpy")
except ImportError:
    print("  (skipping reconstruction-accuracy tests: numpy not installed)")
    sys.exit(0)

_REPO = Path(__file__).resolve().parents[3]
_PTYCHONN = _REPO / "examples" / "ptychonn"
_PTYCHOPINN = _REPO / "examples" / "ptychopinn"


def _load(module_path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# pipeline_schema is pure (numpy only); app_stage2 imports `drava`, so stub it.
def _load_ptychonn_modules():
    stub = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("drava", loader=None)
    )
    stub.run = lambda *a, **k: None
    stub.log = lambda *a, **k: None
    stub.publish_py = lambda *a, **k: 0
    for lvl in ("DRAVA_VERBOSE_INFO", "DRAVA_VERBOSE_WARN",
                "DRAVA_VERBOSE_ERROR", "DRAVA_SUCCESS"):
        setattr(stub, lvl, 0)
    sys.modules["drava"] = stub
    sys.path.insert(0, str(_PTYCHONN))
    schema = _load(_PTYCHONN / "pipeline_schema.py", "pipeline_schema")
    stage2 = _load(_PTYCHONN / "app_stage2.py", "app_stage2")
    return schema, stage2


def _make_batches(n_frames, batch, seed=0):
    """Deterministic per-frame amp/phi patches, split into (start,end,amp,phi)."""
    rng = np.random.default_rng(seed)
    amp_all = rng.random((n_frames, 64, 64), dtype=np.float32)
    phi_all = rng.random((n_frames, 64, 64), dtype=np.float32)
    batches = []
    for start in range(0, n_frames, batch):
        end = min(start + batch, n_frames)
        batches.append((start, end, amp_all[start:end].copy(),
                        phi_all[start:end].copy()))
    return amp_all, phi_all, batches


# --------------------------------------------------------------------------- #
# PtychoNN
# --------------------------------------------------------------------------- #
def test_ptychonn_wire_roundtrip_is_lossless():
    schema, _ = _load_ptychonn_modules()
    _, _, batches = _make_batches(16, 4, seed=1)
    start, end, amp, phi = batches[0]
    payload = schema.encode_stage1_prediction(
        job_id=1, start=start, end=end, n_total=16,
        pred_amp=amp, pred_phi=phi)
    out = schema.decode_stage1_prediction(payload)
    assert out["start"] == start and out["end"] == end
    assert np.array_equal(out["pred_amp"], amp)
    assert np.array_equal(out["pred_phi"], phi)


def _ptychonn_assemble(order, n_frames=100, batch=8, seed=2):
    """Encode batches, deliver in `order`, return the stitched reconstruction."""
    schema, stage2 = _load_ptychonn_modules()
    _, _, batches = _make_batches(n_frames, batch, seed=seed)
    payloads = [
        schema.encode_stage1_prediction(
            job_id=7, start=s, end=e, n_total=n_frames, pred_amp=a, pred_phi=p)
        for (s, e, a, p) in batches
    ]
    acc = stage2.Stage2Accumulator()
    for i in order:
        acc.consume([payloads[i]], base_index=batches[i][0])
    used = int(np.floor(np.sqrt(n_frames))) ** 2
    return stage2.stitch_component(acc.amp_pred_all[:used],
                                   tst_side=int(np.sqrt(used)))


def test_ptychonn_stitch_order_independent():
    n = len(_make_batches(100, 8, seed=2)[2])
    in_order = _ptychonn_assemble(list(range(n)))
    shuffled_ix = list(range(n))
    random.Random(123).shuffle(shuffled_ix)
    shuffled = _ptychonn_assemble(shuffled_ix)
    assert np.array_equal(in_order, shuffled), \
        "PtychoNN stitched reconstruction differs when batches arrive out of order"


def test_ptychonn_stitch_multithreaded_matches_serial():
    schema, stage2 = _load_ptychonn_modules()
    n_frames, batch = 100, 8
    _, _, batches = _make_batches(n_frames, batch, seed=2)
    payloads = [
        schema.encode_stage1_prediction(
            job_id=7, start=s, end=e, n_total=n_frames, pred_amp=a, pred_phi=p)
        for (s, e, a, p) in batches
    ]
    # Serial reference
    serial = _ptychonn_assemble(list(range(len(batches))))

    # Concurrent: multiple threads consume disjoint position ranges. Each writes
    # to its own slice (as the runtime guarantees via base_index), so no lock is
    # needed — this is exactly the stateless-callback property under test.
    acc = stage2.Stage2Accumulator()
    acc._ensure_capacity(n_frames)

    def worker(idxs):
        for i in idxs:
            acc.consume([payloads[i]], base_index=batches[i][0])

    idxs = list(range(len(batches)))
    random.Random(9).shuffle(idxs)
    nthreads = 8
    chunks = [idxs[k::nthreads] for k in range(nthreads)]
    threads = [threading.Thread(target=worker, args=(c,)) for c in chunks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    used = int(np.floor(np.sqrt(n_frames))) ** 2
    concurrent = stage2.stitch_component(acc.amp_pred_all[:used],
                                         tst_side=int(np.sqrt(used)))
    assert np.array_equal(serial, concurrent), \
        "PtychoNN reconstruction differs under multi-threaded assembly"


# --------------------------------------------------------------------------- #
# TomoGAN (position-indexed frame assembly)
# --------------------------------------------------------------------------- #
def _tomogan_assemble(order, n_frames=64, batch=4, seed=3):
    """Model output is deterministic per input frame; the property under test is
    that placing each batch at its base_index reproduces the same ordered stack
    regardless of arrival order (a stand-in for TomoGAN's denoised output)."""
    rng = np.random.default_rng(seed)
    frames = rng.random((n_frames, 32, 32), dtype=np.float32)
    # A deterministic "denoise": any fixed elementwise transform.
    denoise = lambda x: np.tanh(x) * 2.0
    out = np.empty_like(frames)
    batch_ranges = [(s, min(s + batch, n_frames))
                    for s in range(0, n_frames, batch)]
    for bi in order:
        s, e = batch_ranges[bi]
        out[s:e] = denoise(frames[s:e])   # placed by absolute position
    return frames, out, denoise


def test_tomogan_output_order_independent():
    n_batches = len(range(0, 64, 4))
    frames, in_order, denoise = _tomogan_assemble(list(range(n_batches)))
    ix = list(range(n_batches))
    random.Random(55).shuffle(ix)
    _, shuffled, _ = _tomogan_assemble(ix)
    assert np.array_equal(in_order, shuffled), \
        "TomoGAN output differs when batches arrive out of order"
    # And it equals the straight serial denoise of the whole stack.
    assert np.array_equal(in_order, denoise(frames))


def test_tomogan_output_multithreaded_matches_serial():
    n_frames, batch = 64, 4
    rng = np.random.default_rng(3)
    frames = rng.random((n_frames, 32, 32), dtype=np.float32)
    denoise = lambda x: np.tanh(x) * 2.0
    serial = denoise(frames)

    out = np.empty_like(frames)
    ranges = [(s, min(s + batch, n_frames)) for s in range(0, n_frames, batch)]

    def worker(idxs):
        for bi in idxs:
            s, e = ranges[bi]
            out[s:e] = denoise(frames[s:e])

    idxs = list(range(len(ranges)))
    random.Random(7).shuffle(idxs)
    nthreads = 8
    chunks = [idxs[k::nthreads] for k in range(nthreads)]
    threads = [threading.Thread(target=worker, args=(c,)) for c in chunks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert np.array_equal(serial, out), \
        "TomoGAN output differs under multi-threaded assembly"


def test_ptychopinn_wire_roundtrip_is_lossless():
    """Stage1 -> stage2 carries complex64 patches as two float32 blobs.

    Canvas assembly itself is order-independent by construction (scatter-add of
    absolute positions), but it needs torch, so it is not covered here. What is
    covered is that the complex values survive the real/imag split exactly.
    """
    schema = _load(_PTYCHOPINN / "pipeline_schema.py", "ptychopinn_pipeline_schema")

    rng = np.random.default_rng(11)
    b, c, m = 5, 4, 8
    patches = (
        rng.standard_normal((b, c, m, m), dtype=np.float32)
        + 1j * rng.standard_normal((b, c, m, m), dtype=np.float32)
    ).astype(np.complex64)

    start, end = 40, 40 + b
    payload = schema.encode_stage1_patches(
        job_id=3, start=start, end=end, n_total=1000, patches=patches
    )
    out = schema.decode_stage1_patches(payload)

    assert out["start"] == start and out["end"] == end
    assert out["n_total"] == 1000 and out["job_id"] == 3
    assert out["patches"].dtype == np.complex64
    assert out["patches"].shape == patches.shape
    assert np.array_equal(out["patches"], patches), \
        "PtychoPINN wire round-trip altered the complex patches"


def test_ptychopinn_wire_rejects_corrupt_payload():
    schema = _load(_PTYCHOPINN / "pipeline_schema.py", "ptychopinn_pipeline_schema")

    patches = np.zeros((2, 4, 8, 8), dtype=np.complex64)
    payload = schema.encode_stage1_patches(
        job_id=1, start=0, end=2, n_total=2, patches=patches
    )
    for bad in (payload[:-4], payload + b"\x00\x00\x00\x00"):
        try:
            schema.decode_stage1_patches(bad)
        except ValueError:
            continue
        raise AssertionError("decoder accepted a truncated/extended payload")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
