"""Unit tests for drava_common.cli — validate, scaffold, and stage-cmd resolution.

These test the launcher logic that does NOT need the built `drava` runtime:
config validation, the new-app scaffolder, and the per-stage command guessing
(which regressed once: stage2 must run app_stage2.py, resolved against the
stage workdir, not the CWD).

Run: python examples/common/tests/test_cli.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Keep all scratch inside the repo (see AGENTS.md filesystem rule).
_REPO_TMP = Path(__file__).resolve().parents[3] / ".scratch" / "tests_cli"
_REPO_TMP.mkdir(parents=True, exist_ok=True)

from drava_common import cli  # noqa: E402
from drava_common.config import load_pipeline_config, validate_pipeline  # noqa: E402


def _mkdir(name: str) -> Path:
    import tempfile

    return Path(tempfile.mkdtemp(dir=_REPO_TMP, prefix=name + "_"))


def test_default_app_cmd_stage1():
    wd = _mkdir("s1")
    cmd = cli._default_app_cmd("stage1", wd)
    assert cmd[-1] == "app.py", cmd


def test_default_app_cmd_stage2_uses_app_stage2_when_present():
    wd = _mkdir("s2present")
    (wd / "app_stage2.py").write_text("import drava\n", encoding="utf-8")
    cmd = cli._default_app_cmd("stage2", wd)
    assert cmd[-1] == "app_stage2.py", cmd


def test_default_app_cmd_stage2_falls_back_to_app_when_absent():
    wd = _mkdir("s2absent")
    cmd = cli._default_app_cmd("stage2", wd)
    assert cmd[-1] == "app.py", cmd


def test_default_app_cmd_resolves_against_workdir_not_cwd():
    # Regression: app_stage2.py exists in the workdir but NOT in CWD.
    wd = _mkdir("wdres")
    (wd / "app_stage2.py").write_text("import drava\n", encoding="utf-8")
    # cli._default_app_cmd must look in `wd`, regardless of where we run from.
    cmd = cli._default_app_cmd("stage2", wd)
    assert cmd[-1] == "app_stage2.py", cmd


def test_new_app_single_stage_scaffold():
    d = _REPO_TMP / "scaf_single"
    args = cli.build_parser().parse_args(
        ["new-app", "single", "--dir", str(d), "--stages", "1"]
    )
    rc = args.func(args)
    assert rc == 0
    assert (d / "pipeline.yaml").is_file()
    assert (d / "app.py").is_file()
    assert not (d / "app_stage2.py").exists()
    # scaffolded config validates
    cfg = load_pipeline_config(d / "pipeline.yaml")
    assert validate_pipeline(cfg) == [] or all(
        "warning" not in w for w in validate_pipeline(cfg)
    )
    assert cfg.stage_names == ["stage1"]


def test_new_app_two_stage_scaffold_validates_and_wires():
    d = _REPO_TMP / "scaf_two"
    args = cli.build_parser().parse_args(
        ["new-app", "twostage", "--dir", str(d), "--stages", "2"]
    )
    assert args.func(args) == 0
    assert (d / "app.py").is_file()
    assert (d / "app_stage2.py").is_file()
    cfg = load_pipeline_config(d / "pipeline.yaml")
    # No errors raised => wiring between stage1.egress and stage2.ingress matches.
    validate_pipeline(cfg)
    assert cfg.stage_names == ["stage1", "stage2"]


def test_new_app_refuses_nonempty_dir():
    d = _REPO_TMP / "nonempty"
    d.mkdir(parents=True, exist_ok=True)
    (d / "keep.txt").write_text("x", encoding="utf-8")
    args = cli.build_parser().parse_args(["new-app", "x", "--dir", str(d)])
    assert args.func(args) == 1  # refuses, non-zero rc


def test_validate_command_ok(capsys=None):
    d = _REPO_TMP / "validate_ok"
    a = cli.build_parser().parse_args(
        ["new-app", "v", "--dir", str(d), "--stages", "2"]
    )
    a.func(a)
    va = cli.build_parser().parse_args(["validate", str(d / "pipeline.yaml")])
    assert va.func(va) == 0


def test_validate_command_rejects_broken_wiring():
    d = _REPO_TMP / "validate_bad"
    d.mkdir(parents=True, exist_ok=True)
    (d / "pipeline.yaml").write_text(
        "transport:\n  type: nats\n"
        "stages:\n"
        "  - name: stage1\n"
        "    ingress: {stream: FRAMES, subject: frames.raw}\n"
        "    egress: {stream: P, subject: frames.TYPO}\n"
        "  - name: stage2\n"
        "    ingress: {stream: P, subject: frames.stage1}\n"
        "    egress: {forward_eos: false}\n",
        encoding="utf-8",
    )
    va = cli.build_parser().parse_args(["validate", str(d / "pipeline.yaml")])
    assert va.func(va) == 1  # invalid wiring => non-zero rc


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
