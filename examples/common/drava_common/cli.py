"""``drava-pipeline`` — a small launcher/validator/scaffolder for Drava pipelines.

This is the numaflow-like front door for the examples. Instead of opening N
terminals and exporting ``DRAVA_STAGE_NAME`` by hand for each stage, you point
this at a ``pipeline.yaml`` and it:

- validates the config (wiring between stages, EOS forwarding, required fields);
- launches one process per stage with ``DRAVA_STAGE_CONFIG``/``DRAVA_STAGE_NAME``
  set correctly (downstream stages first, so they are listening before upstream
  stages produce);
- streams their output and shuts them all down together on Ctrl-C or failure.

It launches only the runtime stages. Data sources (publishers) stay separate,
matching the runtime's design: the publisher is not the runtime.

Usage:
    drava-pipeline validate pipeline.yaml
    drava-pipeline run pipeline.yaml [--app-cmd stage1=python app.py ...]
    drava-pipeline new-app NAME [--dir DIR] [--stages N]

Run as a module if not installed on PATH:
    python -m drava_common.cli run pipeline.yaml
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .config import (
    PipelineConfig,
    PipelineConfigError,
    load_pipeline_config,
    validate_pipeline,
)


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #
def cmd_validate(args) -> int:
    try:
        cfg = load_pipeline_config(args.config)
        warnings = validate_pipeline(cfg)
    except PipelineConfigError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"OK: {cfg.path} — pipeline '{cfg.name}', transport={cfg.transport_type}")
    print(f"    stages: {' -> '.join(cfg.stage_names)}")
    for w in warnings:
        print(f"    warning: {w}")
    return 0


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
def _default_app_cmd(stage_name: str, workdir: Path) -> list[str]:
    """Guess the per-stage command, resolving files against ``workdir``.

    stage1 -> ``app.py``; stageN -> ``app_stageN.py`` if it exists in workdir,
    else ``app.py``. Existence is checked in ``workdir`` (where the stage
    subprocess runs), not the launcher's CWD.
    """
    if stage_name != "stage1" and (workdir / f"app_{stage_name}.py").is_file():
        return [sys.executable, f"app_{stage_name}.py"]
    return [sys.executable, "app.py"]


def _parse_app_cmd_overrides(pairs: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--app-cmd expects stage=command, got: {pair!r}")
        stage, cmd = pair.split("=", 1)
        out[stage.strip()] = cmd.strip().split()
    return out


def _stream(proc: subprocess.Popen, prefix: str):
    for line in proc.stdout:  # type: ignore[union-attr]
        sys.stdout.write(f"[{prefix}] {line}")
        sys.stdout.flush()


def _parse_nats_host_port(nats_url: str):
    hostport = nats_url.replace("nats://", "").rsplit("/", 1)[0]
    host, _, port = hostport.partition(":")
    host = host or "127.0.0.1"
    if host in ("0.0.0.0", "::", "[::]"):
        host = "127.0.0.1"
    return host, int(port or "4222")


def _nats_reachable(nats_url: str, timeout_s: float = 1.0) -> bool:
    import socket

    host, port = _parse_nats_host_port(nats_url)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _start_nats(nats_command: str, nats_config: str, nats_url: str):
    """Start a local nats-server with JetStream enabled. Returns (proc, logfile)."""
    _host, port = _parse_nats_host_port(nats_url)
    if nats_config:
        cmd = [nats_command, "-c", nats_config]
    else:
        cmd = [nats_command, "-js", "-p", str(port)]
    print(f"[drava-pipeline] starting nats-server: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    t = threading.Thread(target=_stream, args=(proc, "nats"), daemon=True)
    t.start()
    return proc


def _wait_nats(nats_url: str, timeout_s: float = 20.0) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        if _nats_reachable(nats_url, timeout_s=0.5):
            return True
        time.sleep(0.2)
    return False


def cmd_run(args) -> int:
    try:
        cfg = load_pipeline_config(args.config)
        warnings = validate_pipeline(cfg)
    except PipelineConfigError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    overrides = _parse_app_cmd_overrides(args.app_cmd)
    workdir = Path(args.workdir).resolve() if args.workdir else cfg.path.parent
    cfg_abs = str(cfg.path.resolve())

    # For the NATS transport, ensure a server is reachable before launching
    # stages (they FATAL-exit on connect failure). Optionally start one.
    nats_proc = None
    if cfg.transport_type == "nats":
        if args.start_nats:
            nats_proc = _start_nats(args.nats_command, args.nats_config, cfg.nats_url)
            if not _wait_nats(cfg.nats_url):
                print(
                    f"[drava-pipeline] nats-server did not become reachable at "
                    f"{cfg.nats_url}",
                    file=sys.stderr,
                )
                nats_proc.send_signal(signal.SIGINT)
                return 1
            print(f"[drava-pipeline] nats ready ({cfg.nats_url})")
        elif not _nats_reachable(cfg.nats_url):
            print(
                f"[drava-pipeline] no NATS server reachable at {cfg.nats_url}. "
                f"Start one (e.g. `nats-server -js`) or pass --start-nats.",
                file=sys.stderr,
            )
            return 1

    # Launch downstream stages first so they are listening before upstream
    # stages start emitting.
    launch_order = list(reversed(cfg.stages))
    procs: list[tuple[str, subprocess.Popen]] = []
    threads: list[threading.Thread] = []

    def shutdown():
        for _name, p in procs:
            if p.poll() is None:
                try:
                    p.send_signal(signal.SIGINT)
                except Exception:
                    pass
        for _name, p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()

    try:
        for stage in launch_order:
            cmd = overrides.get(stage.name, _default_app_cmd(stage.name, workdir))
            env = dict(os.environ)
            env["DRAVA_STAGE_CONFIG"] = cfg_abs
            env["DRAVA_STAGE_NAME"] = stage.name
            print(f"[drava-pipeline] launching stage '{stage.name}': {' '.join(cmd)}")
            p = subprocess.Popen(
                cmd,
                cwd=str(workdir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            procs.append((stage.name, p))
            t = threading.Thread(target=_stream, args=(p, stage.name), daemon=True)
            t.start()
            threads.append(t)

        print("[drava-pipeline] all stages launched; Ctrl-C to stop.")
        if args.publisher:
            print(f"[drava-pipeline] launching publisher: {args.publisher}")
            penv = dict(os.environ)
            penv["DRAVA_STAGE_CONFIG"] = cfg_abs
            pub = subprocess.Popen(
                args.publisher.split(),
                cwd=str(workdir),
                env=penv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            procs.append(("publisher", pub))
            t = threading.Thread(target=_stream, args=(pub, "publisher"), daemon=True)
            t.start()
            threads.append(t)

        # Monitor: report each process's exit exactly once. If any *stage* exits
        # (for any reason), the pipeline is broken — tear everything down. The
        # publisher exiting is normal (it finishes its data), so we wait for the
        # stages to drain after it does.
        stage_names = {s.name for s in cfg.stages}
        reported: set[str] = set()
        rc = 0
        while True:
            for n, p in procs:
                code = p.poll()
                if code is not None and n not in reported:
                    reported.add(n)
                    if code != 0:
                        print(
                            f"[drava-pipeline] '{n}' exited rc={code}",
                            file=sys.stderr,
                        )
                        rc = rc or code
                    else:
                        print(f"[drava-pipeline] '{n}' finished ok")

            # A stage dying is fatal: stop the whole pipeline now.
            stage_died = any(
                n in stage_names and p.poll() not in (None, 0) for n, p in procs
            )
            if stage_died:
                print(
                    "[drava-pipeline] a stage exited abnormally; shutting down.",
                    file=sys.stderr,
                )
                break

            # Otherwise stop once every process has exited (clean completion).
            if all(p.poll() is not None for _n, p in procs):
                break

            time.sleep(0.3)
        return rc
    except KeyboardInterrupt:
        print("\n[drava-pipeline] interrupted; shutting down stages...")
        return 130
    finally:
        shutdown()
        if nats_proc is not None and nats_proc.poll() is None:
            print("[drava-pipeline] stopping nats-server")
            try:
                nats_proc.send_signal(signal.SIGINT)
                nats_proc.wait(timeout=5)
            except Exception:
                nats_proc.kill()


# --------------------------------------------------------------------------- #
# new-app (scaffolder)
# --------------------------------------------------------------------------- #
_APP_TEMPLATE = '''import drava


def func(frames, base_index):
    """Process one batch of raw frame payloads.

    frames: list[bytes] (the runtime already stripped the EOS marker).
    base_index: global index of frames[0] across the whole stream.
    """
    for i, raw in enumerate(frames):
        # TODO: decode `raw`, run your computation.
        # Transform stages publish downstream with drava.publish_py(result).
        pass


drava.run(func)
'''

_APP_TERMINAL_TEMPLATE = '''import drava

STAGE_NAME = __STAGE__


def func(frames, base_index):
    for raw in frames:
        # TODO: accumulate / process results.
        pass


def finalize(expected_frames):
    # Runs once, after all callbacks drain. Write your final output here.
    print(f"[{STAGE_NAME}-final] frames={expected_frames}")


drava.run(func, on_end_of_stream=finalize)
'''

_PIPELINE_TEMPLATE = """pipeline:
  name: {name}

transport:
  type: nats
  nats_url: nats://127.0.0.1:4222

publisher:
  synthetic: true
  num_frames: 1000
  rate_hz: 1000

stages:
{stages}
"""

_STAGE_TEMPLATE = """  - name: {name}
    runtime:
      threads: 4
      callback_batch: 256
    ingress:
      stream: {in_stream}
      subject: {in_subject}
      durable: {name}_durable
      fetch_batch: 256
      fetch_timeout_ms: 200
{egress}"""


def _stage_block(index: int, total: int, name: str) -> str:
    in_stream = "FRAMES" if index == 0 else f"STAGE{index}_OUT"
    in_subject = "frames.raw" if index == 0 else f"frames.stage{index}"
    if index == total - 1:
        egress = "    egress:\n      forward_eos: false\n"
    else:
        egress = (
            "    egress:\n"
            f"      stream: STAGE{index + 1}_OUT\n"
            f"      subject: frames.stage{index + 1}\n"
        )
    return _STAGE_TEMPLATE.format(
        name=name, in_stream=in_stream, in_subject=in_subject, egress=egress
    )


def cmd_new_app(args) -> int:
    base = Path(args.dir or f"examples/{args.name}").resolve()
    if base.exists() and any(base.iterdir()):
        print(f"refusing to scaffold into non-empty dir: {base}", file=sys.stderr)
        return 1
    base.mkdir(parents=True, exist_ok=True)

    n = max(1, args.stages)
    stage_names = [f"stage{i + 1}" for i in range(n)]
    stages_yaml = "\n".join(_stage_block(i, n, sn) for i, sn in enumerate(stage_names))
    (base / "pipeline.yaml").write_text(
        _PIPELINE_TEMPLATE.format(name=args.name, stages=stages_yaml),
        encoding="utf-8",
    )

    # stage1 app.py; extra stages get app_stageN.py; last stage is terminal.
    for i, sn in enumerate(stage_names):
        terminal = i == n - 1
        if terminal:
            body = _APP_TERMINAL_TEMPLATE.replace("__STAGE__", repr(sn))
        else:
            body = _APP_TEMPLATE
        fname = "app.py" if sn == "stage1" else f"app_{sn}.py"
        (base / fname).write_text(body, encoding="utf-8")

    print(f"scaffolded '{args.name}' in {base}")
    print("  files: pipeline.yaml, " + ", ".join(
        "app.py" if sn == "stage1" else f"app_{sn}.py" for sn in stage_names
    ))
    print(f"  validate: drava-pipeline validate {base / 'pipeline.yaml'}")
    print(f"  run:      drava-pipeline run {base / 'pipeline.yaml'}")
    return 0


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="drava-pipeline",
        description="Validate, run, or scaffold Drava pipelines.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="Validate a pipeline.yaml.")
    v.add_argument("config", help="Path to pipeline.yaml")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="Launch every stage of a pipeline.")
    r.add_argument("config", help="Path to pipeline.yaml")
    r.add_argument(
        "--app-cmd",
        action="append",
        default=[],
        metavar="STAGE=CMD",
        help="Override the command for a stage, e.g. stage1='python app.py'.",
    )
    r.add_argument(
        "--publisher",
        default="",
        help="Optional publisher command to launch after stages are up.",
    )
    r.add_argument(
        "--workdir",
        default="",
        help="Directory to launch stage commands in (default: config's dir).",
    )
    r.add_argument(
        "--start-nats",
        action="store_true",
        help="Start (and stop) a local nats-server -js for the NATS transport.",
    )
    r.add_argument(
        "--nats-command",
        default="nats-server",
        help="nats-server executable used with --start-nats (default: nats-server).",
    )
    r.add_argument(
        "--nats-config",
        default="",
        help="Optional nats-server config file for --start-nats (else -js -p PORT).",
    )
    r.set_defaults(func=cmd_run)

    na = sub.add_parser("new-app", help="Scaffold a new example app.")
    na.add_argument("name", help="App name (used for the dir and pipeline name).")
    na.add_argument("--dir", default="", help="Target dir (default: examples/NAME).")
    na.add_argument("--stages", type=int, default=1, help="Number of stages.")
    na.set_defaults(func=cmd_new_app)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
