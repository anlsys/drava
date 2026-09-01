"""Unit tests for drava_common.config — the single Python pipeline reader.

Run: python -m pytest examples/common/tests -q
Or:  python examples/common/tests/test_config.py   (no pytest needed)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Keep all scratch inside the repo (see AGENTS.md filesystem rule).
_REPO_TMP = Path(__file__).resolve().parents[3] / ".scratch" / "tests"
_REPO_TMP.mkdir(parents=True, exist_ok=True)

from drava_common.config import (  # noqa: E402
    PipelineConfigError,
    load_pipeline_config,
    validate_pipeline,
)

GOOD_TWO_STAGE = """
pipeline:
  name: demo
transport:
  type: nats
  nats_url: nats://127.0.0.1:4222
publisher:
  synthetic: true
  num_frames: 1000
  rate_hz: 500
stages:
  - name: stage1
    runtime:
      threads: 4
      callback_batch: 256
    ingress:
      stream: FRAMES
      subject: frames.raw
      durable: s1
    egress:
      stream: PREDICTIONS
      subject: frames.stage1
  - name: stage2
    runtime:
      threads: 2
    ingress:
      stream: PREDICTIONS
      subject: frames.stage1
      durable: s2
    egress:
      forward_eos: false
"""

BROKEN_WIRING = """
pipeline:
  name: broken
transport:
  type: nats
stages:
  - name: stage1
    ingress:
      stream: FRAMES
      subject: frames.raw
    egress:
      stream: PREDICTIONS
      subject: frames.WRONG
  - name: stage2
    ingress:
      stream: PREDICTIONS
      subject: frames.stage1
    egress:
      forward_eos: false
"""

DUP_NAMES = """
transport:
  type: socket
stages:
  - name: stage1
  - name: stage1
"""


def _write(text: str) -> Path:
    f = tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, dir=_REPO_TMP
    )
    f.write(text)
    f.close()
    return Path(f.name)


def test_load_and_fields():
    cfg = load_pipeline_config(_write(GOOD_TWO_STAGE))
    assert cfg.name == "demo"
    assert cfg.transport_type == "nats"
    assert cfg.stage_names == ["stage1", "stage2"]
    assert cfg.stage("stage1").threads == 4
    assert cfg.stage("stage1").callback_batch == 256
    assert cfg.stage("stage2").egress.get("forward_eos") is False


def test_validate_good():
    cfg = load_pipeline_config(_write(GOOD_TWO_STAGE))
    warnings = validate_pipeline(cfg)
    assert warnings == [], f"expected no warnings, got {warnings}"


def test_validate_broken_wiring():
    cfg = load_pipeline_config(_write(BROKEN_WIRING))
    try:
        validate_pipeline(cfg)
    except PipelineConfigError as exc:
        assert "broken wiring" in str(exc)
    else:
        raise AssertionError("expected PipelineConfigError for broken wiring")


def test_duplicate_stage_names():
    cfg = load_pipeline_config(_write(DUP_NAMES))
    try:
        validate_pipeline(cfg)
    except PipelineConfigError as exc:
        assert "duplicate stage name" in str(exc)
    else:
        raise AssertionError("expected PipelineConfigError for duplicate names")


def test_missing_stage():
    cfg = load_pipeline_config(_write(GOOD_TWO_STAGE))
    try:
        cfg.stage("does_not_exist")
    except PipelineConfigError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected PipelineConfigError for missing stage")


def test_missing_file():
    try:
        load_pipeline_config("/no/such/pipeline.yaml")
    except PipelineConfigError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected PipelineConfigError for missing file")


def test_terminal_forward_eos_warning():
    text = GOOD_TWO_STAGE.replace("      forward_eos: false", "      forward_eos: true")
    cfg = load_pipeline_config(_write(text))
    warnings = validate_pipeline(cfg)
    assert any("terminal stage" in w for w in warnings), warnings


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
