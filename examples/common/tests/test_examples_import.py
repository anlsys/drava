"""Smoke-import the example publisher modules to catch integration mismatches.

This would have caught the TomoGAN publisher bug where
`rate_hz, num_frames = load_publish_config()` unpacked a 3-tuple. Pure imports,
no runtime/NATS/GPU needed: heavy third-party deps (nats, numpy, h5py, imageio,
joblib) are stubbed, and `drava` is stubbed, so importing an example publisher
exercises its own top-level code (imports + config-tuple unpacking in module
scope) without a build.

Run: python examples/common/tests/test_examples_import.py
"""
import importlib
import os
import sys
import types
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_EXAMPLES = _REPO / "examples"
_SCRATCH = _REPO / ".scratch" / "examples_import"
_SCRATCH.mkdir(parents=True, exist_ok=True)


def _install_stub(name: str, attrs: dict | None = None, submodules: dict | None = None):
    mod = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    for subname, subattrs in (submodules or {}).items():
        full = f"{name}.{subname}"
        sub = types.ModuleType(full)
        for k, v in (subattrs or {}).items():
            setattr(sub, k, v)
        sys.modules[full] = sub
        setattr(mod, subname, sub)
    return mod


def _install_all_stubs():
    # drava runtime stub
    _install_stub(
        "drava",
        attrs={
            "run": lambda *a, **k: None,
            "publish_py": lambda *a, **k: 0,
            "log": lambda *a, **k: None,
            "DRAVA_SUCCESS": 0,
            "DRAVA_VERBOSE_INFO": 1,
            "DRAVA_VERBOSE_ERROR": 2,
        },
    )

    # numpy: enough for tobytes/frombuffer-based payload generators
    class _NDArr(list):
        def tobytes(self, *a, **k):
            return b""

    np_attrs = {
        "float32": "float32",
        "zeros": lambda *a, **k: _NDArr(),
        "ndarray": _NDArr,
        "frombuffer": lambda *a, **k: _NDArr(),
    }
    np_random = types.SimpleNamespace(
        default_rng=lambda *a, **k: types.SimpleNamespace(
            random=lambda *a, **k: _NDArr()
        )
    )
    np = _install_stub("numpy", attrs=np_attrs)
    np.random = np_random
    sys.modules["numpy.random"] = np_random

    # nats client + jetstream errors
    class _Client:
        async def connect(self, *a, **k):
            pass

        def jetstream(self):
            return object()

        async def drain(self):
            pass

    _install_stub(
        "nats",
        submodules={
            "aio": {},
            "aio.client": {},  # placeholder; real path set below
            "js": {},
            "js.errors": {"APIError": type("APIError", (Exception,), {"err_code": None})},
        },
    )
    # nats.aio.client.Client is imported by name in some publishers
    aio_client = types.ModuleType("nats.aio.client")
    aio_client.Client = _Client
    sys.modules["nats.aio.client"] = aio_client
    sys.modules["nats.aio"].client = aio_client

    # h5py, imageio, joblib (tomogan/iris deps pulled in via config/util)
    class _H5File:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    _install_stub("h5py", attrs={"File": _H5File})
    _install_stub("imageio", submodules={"v2": {}})
    _install_stub("joblib", attrs={"load": lambda *a, **k: None})


def _import_module_from(path: Path, extra_syspath: Path):
    """Import a .py file as a fresh module with its dir on sys.path."""
    d = str(extra_syspath)
    added = d not in sys.path
    if added:
        sys.path.insert(0, d)
    # ensure a clean import each call
    modname = path.stem
    sys.modules.pop(modname, None)
    try:
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if added:
            sys.path.remove(d)


# Publishers whose *module-scope* code resolves config tuples etc.
_PUBLISHERS = [
    ("ptychonn", "publisher_util.py"),
    ("tomogan", "publisher_util.py"),
]


def _run_with_env(example: str, filename: str):
    ex_dir = _EXAMPLES / example
    cfg = ex_dir / "pipeline.yaml"
    os.environ["DRAVA_STAGE_CONFIG"] = str(cfg) if cfg.exists() else ""
    os.environ["DRAVA_PUBLISH_NUM_FRAMES"] = "8"
    # Clear per-example modules so we import THIS example's own copies.
    for cached in ("publisher_util", "config", "pipeline_schema"):
        sys.modules.pop(cached, None)
    mod = _import_module_from(ex_dir / filename, ex_dir)
    return mod


def test_ptychonn_publisher_util_returns_3tuple():
    _install_all_stubs()
    mod = _run_with_env("ptychonn", "publisher_util.py")
    out = mod.load_publish_config()
    assert len(out) == 3, f"ptychonn load_publish_config expected 3-tuple, got {out!r}"


def test_tomogan_publisher_util_returns_2tuple():
    _install_all_stubs()
    mod = _run_with_env("tomogan", "publisher_util.py")
    out = mod.load_publish_config()
    assert len(out) == 2, f"tomogan load_publish_config expected 2-tuple, got {out!r}"


def test_publisher_modules_import_cleanly():
    # Importing the actual publisher entry modules runs their top-level imports
    # AND (for the socket/js publishers) the module-scope constants. The unpack
    # of load_publish_config happens inside main(), so we import the module and
    # then call a no-op main path where safe. Here we at least ensure import.
    _install_all_stubs()
    for example in ("ptychonn", "tomogan"):
        ex_dir = _EXAMPLES / example
        os.environ["DRAVA_STAGE_CONFIG"] = str(ex_dir / "pipeline.yaml")
        os.environ["DRAVA_PUBLISH_NUM_FRAMES"] = "8"
        for fname in ("publisher_jetstream.py", "publisher_socket.py"):
            # Clear per-example modules so each example imports its OWN
            # publisher_util/config (not a cached one from another example).
            for cached in ("publisher_util", "config", "pipeline_schema"):
                sys.modules.pop(cached, None)
            _import_module_from(ex_dir / fname, ex_dir)


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
