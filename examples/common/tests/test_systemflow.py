"""Unit tests for drava_common.systemflow — the read-only SystemFlow importer.

Run: python -m pytest examples/common/tests -q
Or:  python examples/common/tests/test_systemflow.py   (no pytest needed)

These tests never touch a SystemFlow checkout and never require the
``systemflow`` package to be installed; a model document is just YAML.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Keep all scratch inside the repo (see AGENTS.md filesystem rule).
_REPO_TMP = Path(__file__).resolve().parents[3] / ".scratch" / "tests"
_REPO_TMP.mkdir(parents=True, exist_ok=True)

_REPO_ROOT = Path(__file__).resolve().parents[3]

from drava_common.config import (  # noqa: E402
    load_pipeline_config,
    validate_pipeline,
)
from drava_common.systemflow import (  # noqa: E402
    SystemFlowImportError,
    import_systemflow_pipeline,
    load_systemflow_document,
    pipeline_config_from_mapping,
    systemflow_to_pipeline,
)

TWO_STAGE = """
schema_version: "1.0"
name: demo model

drava:
  pipeline_name: demo
  transport: {type: nats, nats_url: "nats://127.0.0.1:4222"}
  source: {stream: FRAMES, subject: frames.raw}
  benchmark: {app_timeout_s: 45}

graphs:
  - name: main
    nodes:
      - name: Inference
        mutations: [{type: PhaseReconstruction3D}]
        parameters:
          "overlap (%)": 0.4
          "drava threads (n)": 8
          "drava callback batch (n)": 256
          "drava callback serialize (bool)": false
      - name: Assembly
        mutations: [{type: StoreImage}]
        parameters:
          "drava threads (n)": 2
    links:
      - name: "Inference -> Assembly"
        tx: Inference
        rx: Assembly
        parameters:
          "drava stream (str)": PATCHES
          "drava subject (str)": frames.stage1
"""

SINGLE_STAGE = """
schema_version: "1.0"
name: solo
drava:
  pipeline_name: solo
  transport: {type: socket}
graphs:
  - name: only
    nodes:
      - name: Worker
        mutations: [{type: StoreImage}]
        parameters:
          "drava ingress socket path (str)": /tmp/accel_2048.sock
"""

FAN_OUT = """
schema_version: "1.0"
graphs:
  - name: branchy
    nodes:
      - {name: A, mutations: [{type: StoreImage}]}
      - {name: B, mutations: [{type: StoreImage}]}
      - {name: C, mutations: [{type: StoreImage}]}
    links:
      - {name: "A -> B", tx: A, rx: B}
      - {name: "A -> C", tx: A, rx: C}
"""

FAN_IN = """
schema_version: "1.0"
graphs:
  - name: merging
    nodes:
      - {name: A, mutations: [{type: StoreImage}]}
      - {name: B, mutations: [{type: StoreImage}]}
      - {name: C, mutations: [{type: StoreImage}]}
    links:
      - {name: "A -> C", tx: A, rx: C}
      - {name: "B -> C", tx: B, rx: C}
"""

BAD_VERSION = """
schema_version: "2.0"
graphs:
  - name: g
    nodes:
      - {name: A, mutations: [{type: StoreImage}]}
"""

UNKNOWN_KNOB = """
schema_version: "1.0"
graphs:
  - name: g
    nodes:
      - name: A
        mutations: [{type: StoreImage}]
        parameters:
          "drava thredz (n)": 4
"""

MULTI_GRAPH = """
schema_version: "1.0"
graphs:
  - {name: alpha, nodes: [{name: A, mutations: [{type: StoreImage}]}]}
  - {name: beta,  nodes: [{name: B, mutations: [{type: StoreImage}]}]}
"""

SCI_NOTATION = """
schema_version: "1.0"
graphs:
  - name: g
    nodes:
      - name: A
        mutations: [{type: StoreImage}]
        parameters:
          "sample rate (Hz)": 40e6
          "op efficiency (J/op)": 1e-12
"""

DISCONNECTED = """
schema_version: "1.0"
graphs:
  - name: g
    nodes:
      - {name: A, mutations: [{type: StoreImage}]}
      - {name: B, mutations: [{type: StoreImage}]}
"""


def _write(text: str, suffix: str = ".yaml") -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, dir=_REPO_TMP)
    f.write(text)
    f.close()
    return Path(f.name)


def _expect_error(text: str, needle: str, **kwargs):
    path = _write(text)
    try:
        import_systemflow_pipeline(path, **kwargs)
    except SystemFlowImportError as exc:
        assert needle in str(exc), f"expected {needle!r} in error, got: {exc}"
    else:
        raise AssertionError(f"expected SystemFlowImportError mentioning {needle!r}")


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #
def test_two_stage_mapping():
    mapping, cfg = import_systemflow_pipeline(_write(TWO_STAGE))

    assert cfg.name == "demo"
    assert cfg.transport_type == "nats"
    assert cfg.nats_url == "nats://127.0.0.1:4222"
    assert cfg.stage_names == ["stage1", "stage2"]

    s1, s2 = cfg.stages
    assert s1.runtime == {
        "threads": 8,
        "callback_batch": 256,
        "callback_serialize": False,
    }
    assert s1.ingress["stream"] == "FRAMES"
    assert s1.ingress["subject"] == "frames.raw"
    assert s1.egress == {"stream": "PATCHES", "subject": "frames.stage1"}

    assert s2.runtime == {"threads": 2}
    assert s2.ingress["stream"] == "PATCHES"
    assert s2.ingress["subject"] == "frames.stage1"
    # Terminal stage must not forward EOS.
    assert s2.egress == {"forward_eos": False}

    # Passthrough sections survive; physics parameters do not leak in.
    assert mapping["benchmark"] == {"app_timeout_s": 45}
    assert "publisher" not in mapping
    assert "overlap (%)" not in str(mapping["stages"])


def test_generated_pipeline_passes_validate():
    _, cfg = import_systemflow_pipeline(_write(TWO_STAGE))
    # Wiring is derived from the link, so it is consistent by construction.
    assert validate_pipeline(cfg) == []


def test_durables_are_unique_and_derived():
    _, cfg = import_systemflow_pipeline(_write(TWO_STAGE))
    durables = [s.ingress.get("durable") for s in cfg.stages]
    assert durables == ["drava_demo_stage1", "drava_demo_stage2"]
    assert len(set(durables)) == len(durables)


def test_provenance_block_records_source_nodes():
    mapping, _ = import_systemflow_pipeline(_write(TWO_STAGE))
    prov = mapping["systemflow"]
    assert prov["graph"] == "main"
    assert prov["model_name"] == "demo model"
    assert prov["schema_version"] == "1.0"
    assert prov["stage_nodes"] == {"stage1": "Inference", "stage2": "Assembly"}


def test_single_stage_socket_transport():
    mapping, cfg = import_systemflow_pipeline(_write(SINGLE_STAGE))
    assert cfg.transport_type == "socket"
    assert "nats_url" not in mapping["transport"]
    assert cfg.stage_names == ["stage1"]
    s1 = cfg.stages[0]
    # socket transport must not invent NATS stream/subject/durable
    assert s1.ingress == {"socket_path": "/tmp/accel_2048.sock"}
    assert s1.egress == {"forward_eos": False}


def test_scientific_notation_parses_as_float():
    # SystemFlow patches PyYAML's float resolver; we replicate it so `40e6`
    # is a float, not the string "40e6".
    doc, _ = load_systemflow_document(_write(SCI_NOTATION))
    params = doc["graphs"][0]["nodes"][0]["parameters"]
    assert isinstance(params["sample rate (Hz)"], float)
    assert params["sample rate (Hz)"] == 40e6
    assert isinstance(params["op efficiency (J/op)"], float)


def test_graph_selection():
    path = _write(MULTI_GRAPH)
    _, cfg = import_systemflow_pipeline(path, graph="beta")
    assert cfg.stages[0].name == "stage1"
    mapping, _ = import_systemflow_pipeline(path, graph="beta")
    assert mapping["systemflow"]["stage_nodes"] == {"stage1": "B"}


def test_mapping_round_trips_through_pipeline_config():
    mapping, cfg = import_systemflow_pipeline(_write(TWO_STAGE))
    again = pipeline_config_from_mapping(mapping, cfg.path)
    assert again.stage_names == cfg.stage_names
    assert again.raw is mapping


# --------------------------------------------------------------------------- #
# Errors: the importer must refuse to guess
# --------------------------------------------------------------------------- #
def test_fan_out_rejected():
    _expect_error(FAN_OUT, "fans out")


def test_fan_in_rejected():
    _expect_error(FAN_IN, "fans in")


def test_disconnected_nodes_rejected():
    _expect_error(DISCONNECTED, "exactly one source node")


def test_unsupported_schema_version_rejected():
    _expect_error(BAD_VERSION, "unsupported SystemFlow schema_version")


def test_unknown_drava_parameter_rejected():
    # A typo must fail loudly rather than being silently dropped.
    _expect_error(UNKNOWN_KNOB, "unrecognized drava parameter")


def test_ambiguous_graph_rejected():
    _expect_error(MULTI_GRAPH, "pick one with --graph")


def test_named_graph_missing_rejected():
    _expect_error(MULTI_GRAPH, "no graph named", graph="gamma")


def test_missing_file_rejected():
    try:
        load_systemflow_document(_REPO_TMP / "definitely_not_here.yaml")
    except SystemFlowImportError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected SystemFlowImportError for a missing file")


def test_wrong_type_for_knob_rejected():
    bad = TWO_STAGE.replace('"drava threads (n)": 8', '"drava threads (n)": "eight"')
    _expect_error(bad, "must be a number")


def test_non_mapping_document_rejected():
    try:
        load_systemflow_document(_write("- just\n- a\n- list\n"))
    except SystemFlowImportError as exc:
        assert "must be a mapping" in str(exc)
    else:
        raise AssertionError("expected SystemFlowImportError for a non-mapping doc")


# --------------------------------------------------------------------------- #
# The shipped PtychoPINN model must reproduce the checked-in pipeline.yaml
# --------------------------------------------------------------------------- #
def test_ptychopinn_model_matches_checked_in_pipeline():
    model = _REPO_ROOT / "examples" / "ptychopinn" / "systemflow_model.yaml"
    checked_in = _REPO_ROOT / "examples" / "ptychopinn" / "pipeline.yaml"
    if not model.exists() or not checked_in.exists():  # pragma: no cover
        print("SKIP ptychopinn comparison (example files absent)")
        return

    mapping, generated = import_systemflow_pipeline(model)
    expected = load_pipeline_config(checked_in)

    def shape(cfg):
        return (
            cfg.name,
            cfg.transport_type,
            cfg.nats_url,
            [
                (s.name, s.runtime, s.ingress, s.egress, s.metrics)
                for s in cfg.stages
            ],
        )

    assert shape(generated) == shape(expected), (
        "systemflow_model.yaml no longer reproduces the checked-in "
        "examples/ptychopinn/pipeline.yaml"
    )
    assert mapping["publisher"] == expected.raw["publisher"]
    assert mapping["benchmark"] == expected.raw["benchmark"]
    assert validate_pipeline(generated) == []


def test_ptychopinn_model_is_valid_systemflow_schema():
    """The document must stay loadable by SystemFlow itself.

    Loads SystemFlow's own ``io/schema.py`` straight from the read-only
    checkout when it is present, so a drift in either project is caught.
    Skipped when the checkout is not alongside this repo.
    """
    schema_path = (
        _REPO_ROOT.parent / "system_flow" / "systemflow" / "io" / "schema.py"
    )
    if not schema_path.exists():
        print("SKIP systemflow schema check (system_flow checkout not present)")
        return

    import importlib.util

    spec = importlib.util.spec_from_file_location("sf_schema", schema_path)
    sf_schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sf_schema)

    model = _REPO_ROOT / "examples" / "ptychopinn" / "systemflow_model.yaml"
    doc, _ = load_systemflow_document(model)
    parsed = sf_schema.parse_document(doc)
    assert [g.name for g in parsed.graphs] == ["ptychopinn inference"]
    # SystemFlow ignores our extra top-level section, which is what makes the
    # shared document safe for both projects.
    assert "drava" in doc
    assert not hasattr(parsed, "drava")


def test_systemflow_package_is_not_required():
    """The importer must work with `systemflow` absent from sys.modules."""
    saved = {k: v for k, v in sys.modules.items() if k.split(".")[0] == "systemflow"}
    for k in saved:
        del sys.modules[k]
    sys.modules["systemflow"] = None  # force ImportError on `import systemflow`
    try:
        doc, _ = load_systemflow_document(_write(SCI_NOTATION))
        # The replicated float resolver must still apply.
        assert doc["graphs"][0]["nodes"][0]["parameters"]["sample rate (Hz)"] == 40e6
        mapping = systemflow_to_pipeline(doc, source_path="x.yaml")
        assert mapping["stages"][0]["name"] == "stage1"
    finally:
        del sys.modules["systemflow"]
        sys.modules.update(saved)


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
