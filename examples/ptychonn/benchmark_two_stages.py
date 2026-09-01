#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
import yaml

# Drava runtime metrics are read from the per-stage JSONL files the runtime
# writes (DRAVA_METRICS_FILE), and publisher metrics from the JSON file the
# publisher writes (DRAVA_PUBLISHER_METRICS_FILE). Only stage2's finalize line
# is still parsed from stdout.
STAGE2_FINAL_RE = re.compile(
    r"\[stage2-final\]\s+frames=(?P<frames>\d+)\s+stitched_frames=(?P<stitched>\d+)\s+"
    r"stitch_side=(?P<side>\d+)"
)


def read_publisher_metrics(path: Path):
    """Return the publisher's single JSON metrics object, or None if the file is
    not present/complete yet."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_metrics_record(path: Path, stage=None, reasons=("rx_eos", "tx_eos")):
    """Return the last JSON metrics record in the runtime's metrics file that
    matches the given stage and reason, or None if not present yet."""
    if not path.exists():
        return None
    record = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if reasons is not None and obj.get("reason") not in reasons:
            continue
        if stage is not None and obj.get("stage") != stage:
            continue
        record = obj
    return record


def parse_args():
    p = argparse.ArgumentParser(description="Run PtychoNN two-stage benchmark matrix.")
    p.add_argument("--batches", default="128,256,512", help="Comma-separated stage1 infer batch sizes.")
    p.add_argument("--max-retries", type=int, default=3,
                   help="Retries per run on intermittent native runtime crashes (e.g. XKRT free() abort).")
    p.add_argument("--timeout-ms", type=int, default=500, help="DRAVA_FETCH_TIMEOUT_MS.")
    p.add_argument("--threads", type=int, default=None,
                   help="Worker threads for both stages. Overrides runtime.threads "
                        "in the stage config; if unset, the config value is used.")
    p.add_argument("--stage1-threads", type=int, default=None, help="Override DRAVA_THREADS for stage1.")
    p.add_argument("--stage2-threads", type=int, default=None, help="Override DRAVA_THREADS for stage2.")
    p.add_argument("--stage1-callback-batch", type=int, default=None,
                   help="Override DRAVA_CALLBACK_BATCH for stage1.")
    p.add_argument("--stage2-callback-batch", type=int, default=None,
                   help="Override DRAVA_CALLBACK_BATCH for stage2.")
    p.add_argument("--xkaapi-verbose", type=int, default=4, help="XKAAPI_VERBOSE.")
    p.add_argument("--rate-hz", type=int, default=None, help="DRAVA_PUBLISH_RATE_HZ (<=0 means max speed).")
    p.add_argument("--num-frames", type=int, default=0, help="DRAVA_PUBLISH_NUM_FRAMES. Overrides duration mode.")
    p.add_argument("--runs", type=int, default=1, help="Runs per batch.")
    p.add_argument("--python", default=sys.executable, help="Python executable.")
    p.add_argument("--reuse-nats", action="store_true", help="Use existing NATS server.")
    p.add_argument("--nats-url", default="", help="NATS URL. Defaults to transport.nats_url from --stage-config.")
    p.add_argument("--nats-config", default="nats.conf",
                   help="NATS server config path used when starting a local nats-server.")
    p.add_argument("--stage-config", default="pipeline.yaml", help="Stage config YAML path.")
    p.add_argument("--out-dir", default="bench_logs_two_stages", help="Output dir under examples/ptychonn.")
    p.add_argument("--app-timeout-s", type=float, default=None,
                   help="Wait for runtime/final logs after publisher exits.")
    p.add_argument("--input-stream", default="FRAMES", help="Publisher->Stage1 stream.")
    p.add_argument("--input-subject", default="frames.raw", help="Publisher->Stage1 subject.")
    p.add_argument("--output-stream", default="PREDICTIONS", help="Stage1->Stage2 stream.")
    p.add_argument("--output-subject", default="frames.stage1", help="Stage1->Stage2 subject.")
    p.add_argument("--stage1-durable-prefix", default="drava_stage1_bench", help="Stage1 durable prefix.")
    p.add_argument("--stage2-durable-prefix", default="drava_stage2_bench", help="Stage2 durable prefix.")
    return p.parse_args()


def parse_stage_ingress_value(path: Path, stage_name: str, key_name: str):
    if not path.exists():
        return None
    in_stages = False
    in_target = False
    in_ingress = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if body == "stages:":
            in_stages = True
            in_target = False
            in_ingress = False
            continue
        if not in_stages:
            continue
        if indent == 2 and body.startswith("- "):
            in_target = False
            in_ingress = False
            kv = body[2:]
            if kv.startswith("name:") and kv.split(":", 1)[1].strip().strip("\"'") == stage_name:
                in_target = True
            continue
        if not in_target:
            continue
        if indent == 4 and body == "ingress:":
            in_ingress = True
            continue
        if indent == 4 and body.endswith(":") and body != "ingress:":
            in_ingress = False
            continue
        if in_ingress and indent >= 6 and ":" in body:
            key, value = body.split(":", 1)
            if key.strip() == key_name:
                return value.strip().strip("\"'")
    return None


def parse_stage_runtime_value(path: Path, stage_name: str, key_name: str):
    if not path.exists():
        return None
    in_stages = False
    in_target = False
    in_runtime = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if body == "stages:":
            in_stages = True
            in_target = False
            in_runtime = False
            continue
        if not in_stages:
            continue
        if indent == 2 and body.startswith("- "):
            in_target = False
            in_runtime = False
            kv = body[2:]
            if kv.startswith("name:") and kv.split(":", 1)[1].strip().strip("\"'") == stage_name:
                in_target = True
            continue
        if not in_target:
            continue
        if indent == 4 and body == "runtime:":
            in_runtime = True
            continue
        if indent == 4 and body.endswith(":") and body != "runtime:":
            in_runtime = False
            continue
        if in_runtime and indent >= 6 and ":" in body:
            key, value = body.split(":", 1)
            if key.strip() == key_name:
                return value.strip().strip("\"'")
    return None


def parse_publisher_value(path: Path, key_name: str):
    return parse_section_value(path, "publisher", key_name)


def parse_transport_value(path: Path, key_name: str):
    return parse_section_value(path, "transport", key_name)


def parse_section_value(path: Path, section_name: str, key_name: str):
    if not path.exists():
        return None
    in_section = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0 and body == f"{section_name}:":
            in_section = True
            continue
        if indent == 0 and body.endswith(":") and body != f"{section_name}:":
            in_section = False
            continue
        if in_section and indent >= 2 and ":" in body:
            key, value = body.split(":", 1)
            if key.strip() == key_name:
                return value.strip().strip("\"'")
    return None


def parse_nats_config_value(path: Path, key_name: str):
    if not path.exists():
        return None
    pattern = re.compile(rf"^\s*{re.escape(key_name)}\s*[:=]\s*(.*?)\s*$")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            return m.group(1).strip().strip("\"'")
    return None


def nats_url_from_config(path: Path):
    host = parse_nats_config_value(path, "host") or parse_nats_config_value(path, "addr")
    port = parse_nats_config_value(path, "port")
    if port is None:
        return None
    if host is None or host in ("0.0.0.0", "::", "[::]"):
        host = "127.0.0.1"
    return f"nats://{host}:{port}"


def load_yaml_config(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Top-level YAML config must be a mapping: {path}")
    return data


def write_yaml_config(path: Path, config: dict):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)


def _stage_by_name(config: dict, stage_name: str):
    stages = config.get("stages", [])
    if not isinstance(stages, list):
        raise RuntimeError("Config field 'stages' must be a list")
    for stage in stages:
        if isinstance(stage, dict) and stage.get("name") == stage_name:
            return stage
    raise RuntimeError(f"Stage '{stage_name}' not found in config")


def build_run_config(base_config: dict,
                     run_tag: str,
                     nats_url: str,
                     input_stream: str,
                     input_subject: str,
                     output_stream: str,
                     output_subject: str,
                     configured_num_frames: int,
                     rate_hz: int,
                     effective_app_timeout_s: float,
                     stage1_threads: int,
                     stage2_threads: int,
                     stage1_callback_batch: int,
                     stage2_callback_batch: int,
                     timeout_ms: int,
                     stage1_durable: str,
                     stage2_durable: str):
    config = {
        "pipeline": dict(base_config.get("pipeline", {})),
        "transport": dict(base_config.get("transport", {})),
        "publisher": dict(base_config.get("publisher", {})),
        "benchmark": dict(base_config.get("benchmark", {})),
        "stages": [dict(stage) for stage in base_config.get("stages", [])],
    }

    transport = config.setdefault("transport", {})
    transport["nats_url"] = nats_url

    publisher = config.setdefault("publisher", {})
    publisher["rate_hz"] = rate_hz
    publisher["synthetic"] = True
    publisher["num_frames"] = configured_num_frames

    benchmark = config.setdefault("benchmark", {})
    benchmark["app_timeout_s"] = effective_app_timeout_s

    stage1 = _stage_by_name(config, "stage1")
    stage2 = _stage_by_name(config, "stage2")

    stage1_runtime = dict(stage1.get("runtime", {}))
    stage1_runtime["threads"] = stage1_threads
    stage1_runtime["callback_batch"] = stage1_callback_batch
    stage1["runtime"] = stage1_runtime

    stage2_runtime = dict(stage2.get("runtime", {}))
    stage2_runtime["threads"] = stage2_threads
    stage2_runtime["callback_batch"] = stage2_callback_batch
    stage2["runtime"] = stage2_runtime

    stage1_ingress = dict(stage1.get("ingress", {}))
    stage1_ingress["stream"] = input_stream
    stage1_ingress["subject"] = input_subject
    stage1_ingress["durable"] = stage1_durable
    stage1_ingress["fetch_timeout_ms"] = timeout_ms
    stage1["ingress"] = stage1_ingress

    stage1_egress = dict(stage1.get("egress", {}))
    stage1_egress["stream"] = output_stream
    stage1_egress["subject"] = output_subject
    stage1["egress"] = stage1_egress

    stage2_ingress = dict(stage2.get("ingress", {}))
    stage2_ingress["stream"] = output_stream
    stage2_ingress["subject"] = output_subject
    stage2_ingress["durable"] = stage2_durable
    stage2_ingress["fetch_timeout_ms"] = timeout_ms
    stage2["ingress"] = stage2_ingress

    return config


def stream_lines(proc, log_path, line_cb=None):
    with open(log_path, "w", encoding="utf-8") as f:
        for line in proc.stdout:
            f.write(line)
            f.flush()
            if line_cb is not None:
                line_cb(line.rstrip("\n"))


def tail_text(path: Path, n: int = 40):
    if not path.exists():
        return "<no log file>"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-n:])


def fail_with_logs(run_dir: Path, message: str):
    raise RuntimeError(f"{message}\n--- logs ---\n{run_dir}")


def fail_stage_startup(run_dir: Path,
                       message: str,
                       stage1_proc: subprocess.Popen,
                       stage2_proc: subprocess.Popen,
                       stage1_log: Path,
                       stage2_log: Path,
                       nats_log: Path | None = None):
    stage1_rc = stage1_proc.poll()
    stage2_rc = stage2_proc.poll()
    terminate_proc(stage1_proc)
    terminate_proc(stage2_proc)
    details = (
        f"{message}\n"
        f"stage1_rc={stage1_rc} stage2_rc={stage2_rc}\n"
        f"--- stage1 tail ---\n{tail_text(stage1_log)}\n"
        f"--- stage2 tail ---\n{tail_text(stage2_log)}"
    )
    if nats_log is not None:
        details += f"\n--- nats tail ---\n{tail_text(nats_log)}"
    fail_with_logs(run_dir, details)


def parse_nats_host_port(nats_url: str):
    host_port = nats_url.replace("nats://", "")
    if ":" not in host_port:
        raise RuntimeError(f"Invalid --nats-url: {nats_url}")
    return host_port.rsplit(":", 1)


def replace_top_level_config_value(text: str, key: str, value: str):
    pattern = re.compile(rf"(?m)^(\s*{re.escape(key)}\s*[:=]\s*).*$")
    if pattern.search(text):
        return pattern.sub(rf"\g<1>{value}", text, count=1)
    return f"{key}: {value}\n{text}"


def replace_jetstream_store_dir(text: str, store_dir: Path):
    value = json.dumps(str(store_dir))
    pattern = re.compile(r"(?m)^(\s*store_dir\s*[:=]\s*).*$")
    if pattern.search(text):
        return pattern.sub(rf"\g<1>{value}", text, count=1)
    block_pattern = re.compile(r"(jetstream\s*\{)")
    if block_pattern.search(text):
        return block_pattern.sub(rf"\1\n    store_dir: {value}", text, count=1)
    return f"{text.rstrip()}\n\njetstream {{\n    store_dir: {value}\n}}\n"


def write_effective_nats_config(template_path: Path,
                                output_path: Path,
                                nats_url: str,
                                store_dir: Path):
    if not template_path.exists():
        raise RuntimeError(f"NATS config not found: {template_path}")
    _host, port = parse_nats_host_port(nats_url)
    text = template_path.read_text(encoding="utf-8")
    text = replace_top_level_config_value(text, "port", port)
    text = replace_jetstream_store_dir(text, store_dir)
    output_path.write_text(text, encoding="utf-8")


def start_nats(run_dir: Path, nats_url: str, nats_config_path: Path):
    store_dir = run_dir / "nats-store"
    effective_config_path = run_dir / "nats.generated.conf"
    write_effective_nats_config(nats_config_path, effective_config_path,
                                nats_url, store_dir)
    cmd = ["nats-server", "-c", str(effective_config_path)]
    log_path = run_dir / "nats.log"
    f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
    return proc, f, log_path


def wait_for_log_line(path: Path, pattern: str, timeout_s: float):
    end = time.time() + timeout_s
    while time.time() < end:
        if path.exists():
            txt = path.read_text(encoding="utf-8", errors="ignore")
            if pattern in txt:
                return True
            if "address already in use" in txt.lower():
                return False
        time.sleep(0.2)
    return False


def terminate_proc(proc: subprocess.Popen, grace_s=3.0):
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=grace_s)
    except Exception:
        try:
            proc.terminate()
            proc.wait(timeout=grace_s)
        except Exception:
            proc.kill()


def fmt(x, f="{:.2f}"):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return f.format(x)


def run_one(args, base_env, run_dir: Path, batch_size: int, run_idx: int):
    row = {
        "batch": batch_size,
        "run": run_idx,
        "stage1_threads": None,
        "stage2_threads": None,
        "timeout_ms": args.timeout_ms,
        "total_frames": None,
        "publisher_avg_fps": None,
        "publisher_time_s": None,
        "stage1_total_fps": None,
        "stage1_total_time_s": None,
        "stage2_total_fps": None,
        "stage2_total_time_s": None,
        "stage2_side": None,
        "pipeline_e2e_s": None,
    }

    root = Path(__file__).resolve().parent
    stage_config_path = (root / args.stage_config).resolve() if not Path(args.stage_config).is_absolute() else Path(
        args.stage_config)
    nats_config_path = (root / args.nats_config).resolve() if not Path(args.nats_config).is_absolute() else Path(
        args.nats_config)
    base_config = load_yaml_config(stage_config_path)
    base_input_stream = args.input_stream
    base_input_subject = parse_stage_ingress_value(stage_config_path, "stage1", "subject") or args.input_subject
    base_output_stream = args.output_stream
    base_output_subject = args.output_subject
    nats_url = (
            args.nats_url
            or nats_url_from_config(nats_config_path)
            or parse_transport_value(stage_config_path, "nats_url")
            or "nats://127.0.0.1:4222"
    )
    yaml_num_frames = parse_publisher_value(stage_config_path, "num_frames")
    yaml_rate_hz = parse_publisher_value(stage_config_path, "rate_hz")
    yaml_app_timeout_s = parse_section_value(stage_config_path, "benchmark", "app_timeout_s")
    yaml_stage1_threads = parse_stage_runtime_value(stage_config_path, "stage1", "threads")
    yaml_stage2_threads = parse_stage_runtime_value(stage_config_path, "stage2", "threads")
    yaml_stage1_callback_batch = (
            parse_stage_runtime_value(stage_config_path, "stage1", "callback_batch")
            or parse_stage_ingress_value(stage_config_path, "stage1", "callback_batch")
    )
    yaml_stage2_callback_batch = (
            parse_stage_runtime_value(stage_config_path, "stage2", "callback_batch")
            or parse_stage_ingress_value(stage_config_path, "stage2", "callback_batch")
    )
    configured_num_frames = (
        args.num_frames if args.num_frames > 0
        else (int(yaml_num_frames) if yaml_num_frames is not None else 0)
    )
    effective_app_timeout_s = (
        float(args.app_timeout_s)
        if args.app_timeout_s is not None
        else float(yaml_app_timeout_s) if yaml_app_timeout_s is not None
        else 45.0
    )
    # Precedence: per-stage flag > --threads (explicit) > stage config > 1.
    stage1_threads = (
        args.stage1_threads
        if args.stage1_threads is not None
        else args.threads
        if args.threads is not None
        else int(yaml_stage1_threads) if yaml_stage1_threads is not None
        else 1
    )
    stage2_threads = (
        args.stage2_threads
        if args.stage2_threads is not None
        else args.threads
        if args.threads is not None
        else int(yaml_stage2_threads) if yaml_stage2_threads is not None
        else 1
    )
    # The NATS transport dedicates one worker thread (tid 0) to JetStream I/O;
    # with callback_serialize=false the callbacks run on the *other* threads, so
    # a stage needs at least 2 threads or no frames are ever processed.
    for name, nthreads in (("stage1", stage1_threads), ("stage2", stage2_threads)):
        if nthreads is not None and nthreads < 2:
            raise SystemExit(
                f"{name} threads={nthreads} is invalid for the NATS transport: "
                f"one thread is reserved for I/O, leaving no worker to run the "
                f"callback. Use --threads >= 2 (or set callback_serialize: true)."
            )

    stage1_callback_batch = (
        args.stage1_callback_batch
        if args.stage1_callback_batch is not None
        else int(yaml_stage1_callback_batch) if yaml_stage1_callback_batch is not None
        else batch_size
    )
    stage2_callback_batch = (
        args.stage2_callback_batch
        if args.stage2_callback_batch is not None
        else int(yaml_stage2_callback_batch) if yaml_stage2_callback_batch is not None
        else batch_size
    )
    row["stage1_threads"] = stage1_threads
    row["stage2_threads"] = stage2_threads

    env_common = dict(base_env)
    env_common["XKAAPI_VERBOSE"] = str(args.xkaapi_verbose)

    run_tag = f"{run_dir.name}_b{batch_size}_r{run_idx}"
    input_stream = f"{base_input_stream}_{run_tag}"
    input_subject = f"{base_input_subject}.{run_tag}"
    output_stream = f"{base_output_stream}_{run_tag}"
    output_subject = f"{base_output_subject}.{run_tag}"
    stage1_job_id = str(abs(hash(run_tag)) % 2147483647 or 1)
    stage1_durable = f"{args.stage1_durable_prefix}_{run_tag}"
    stage2_durable = f"{args.stage2_durable_prefix}_{run_tag}"
    run_config_path = run_dir / f"pipeline_b{batch_size}_r{run_idx}.yaml"
    run_config = build_run_config(
        base_config=base_config,
        run_tag=run_tag,
        nats_url=nats_url,
        input_stream=input_stream,
        input_subject=input_subject,
        output_stream=output_stream,
        output_subject=output_subject,
        configured_num_frames=configured_num_frames,
        rate_hz=int(args.rate_hz) if args.rate_hz is not None else int(yaml_rate_hz or 0),
        effective_app_timeout_s=effective_app_timeout_s,
        stage1_threads=stage1_threads,
        stage2_threads=stage2_threads,
        stage1_callback_batch=stage1_callback_batch,
        stage2_callback_batch=stage2_callback_batch,
        timeout_ms=args.timeout_ms,
        stage1_durable=stage1_durable,
        stage2_durable=stage2_durable,
    )
    write_yaml_config(run_config_path, run_config)

    stage1_metrics_path = run_dir / f"metrics_stage1_b{batch_size}_r{run_idx}.jsonl"
    stage2_metrics_path = run_dir / f"metrics_stage2_b{batch_size}_r{run_idx}.jsonl"

    env_stage1 = dict(env_common)
    env_stage1["DRAVA_STAGE_CONFIG"] = str(run_config_path)
    # Runtime knobs (threads, callback_batch) come from the per-run
    # pipeline.yaml written above; the runtime does NOT read env vars for those.
    # DRAVA_INFER_BATCH is an *app-side* var (app.py warmup batch, via config.py)
    # so it is still set here. DRAVA_STAGE1_CALLBACK_BATCH was dead (assigned in
    # config.py but never consumed) and has been removed.
    env_stage1["DRAVA_INFER_BATCH"] = str(batch_size)
    env_stage1["DRAVA_STAGE_NAME"] = "stage1"
    env_stage1["STAGE1_JOB_ID"] = stage1_job_id
    env_stage1["DRAVA_METRICS_FILE"] = str(stage1_metrics_path)

    env_stage2 = dict(env_common)
    env_stage2["DRAVA_STAGE_CONFIG"] = str(run_config_path)
    env_stage2["DRAVA_STAGE_NAME"] = "stage2"
    env_stage2["DRAVA_METRICS_FILE"] = str(stage2_metrics_path)

    pub_metrics_path = run_dir / f"pub_metrics_b{batch_size}_r{run_idx}.json"
    env_pub = dict(env_common)
    env_pub["DRAVA_STAGE_CONFIG"] = str(run_config_path)
    env_pub["DRAVA_PUBLISHER_METRICS_FILE"] = str(pub_metrics_path)

    stage1_log = run_dir / f"app_stage1_b{batch_size}_r{run_idx}.log"
    stage2_log = run_dir / f"app_stage2_b{batch_size}_r{run_idx}.log"
    pub_log = run_dir / f"pub_b{batch_size}_r{run_idx}.log"

    stage1_ready = threading.Event()
    stage2_ready = threading.Event()
    stage2_final = {}
    # Publisher metrics come from DRAVA_PUBLISHER_METRICS_FILE (read below), not
    # stdout. pub_first_frame is captured from the publisher's first-frame log to
    # measure end-to-end latency from the first send (matching the pvaPy baseline,
    # which starts timing at its release signal).
    marks = {"pub_start": None, "pub_first_frame": None, "stage2_final": None}

    def on_stage1_line(line: str):
        if "JetStream ready:" in line:
            stage1_ready.set()

    def on_stage2_line(line: str):
        if "JetStream ready:" in line:
            stage2_ready.set()
        m = STAGE2_FINAL_RE.search(line)
        if m:
            stage2_final.update(m.groupdict())
            marks["stage2_final"] = time.monotonic()

    def on_pub_line(line: str):
        # Mark the actual first-frame send (harness clock) so end-to-end latency
        # excludes publisher process/connection startup and matches the pvaPy
        # baseline, which starts timing at its release signal (first frame).
        # Publisher throughput/frames come from the metrics file, not stdout.
        if marks.get("pub_first_frame") is None and "first frame at" in line:
            marks["pub_first_frame"] = time.monotonic()

    print(f"[batch={batch_size} run={run_idx}] starting app_stage2.py")
    stage2_proc = subprocess.Popen(
        [args.python, "app_stage2.py"],
        cwd=root,
        env=env_stage2,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    stage2_thread = threading.Thread(target=stream_lines, args=(stage2_proc, stage2_log, on_stage2_line), daemon=True)
    stage2_thread.start()

    print(f"[batch={batch_size} run={run_idx}] starting app.py")
    stage1_proc = subprocess.Popen(
        [args.python, "app.py"],
        cwd=root,
        env=env_stage1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    stage1_thread = threading.Thread(target=stream_lines, args=(stage1_proc, stage1_log, on_stage1_line), daemon=True)
    stage1_thread.start()

    ready_deadline = time.time() + 120.0
    while time.time() < ready_deadline:
        if stage1_ready.is_set() and stage2_ready.is_set():
            break
        if stage1_proc.poll() is not None or stage2_proc.poll() is not None:
            break
        time.sleep(0.2)

    nats_log = run_dir / "nats.log"
    if stage1_proc.poll() is not None:
        fail_stage_startup(run_dir, "stage1 exited early", stage1_proc,
                           stage2_proc, stage1_log, stage2_log, nats_log)
    if stage2_proc.poll() is not None:
        fail_stage_startup(run_dir, "stage2 exited early", stage1_proc,
                           stage2_proc, stage1_log, stage2_log, nats_log)
    if not (stage1_ready.is_set() and stage2_ready.is_set()):
        fail_stage_startup(run_dir, "stage startup timed out before JetStream ready",
                           stage1_proc, stage2_proc, stage1_log, stage2_log,
                           nats_log)

    print(f"[batch={batch_size} run={run_idx}] starting publisher_jetstream.py")
    marks["pub_start"] = time.monotonic()
    pub_proc = subprocess.Popen(
        [args.python, "publisher_jetstream.py"],
        cwd=root,
        env=env_pub,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log, on_pub_line), daemon=True)
    pub_thread.start()

    pub_timeout_s = max(120, int(max(1, configured_num_frames) / 1000) + 120)
    pub_proc.wait(timeout=pub_timeout_s)
    pub_thread.join(timeout=5)
    pub_done = read_publisher_metrics(pub_metrics_path)

    stage1_metrics = None
    stage2_metrics = None
    end_wait = time.time() + effective_app_timeout_s
    while time.time() < end_wait and (
            stage1_metrics is None
            or stage2_metrics is None
            or not stage2_final
    ):
        if stage1_metrics is None:
            stage1_metrics = read_metrics_record(stage1_metrics_path, stage="stage1")
        if stage2_metrics is None:
            stage2_metrics = read_metrics_record(stage2_metrics_path, stage="stage2")
        if stage1_proc.poll() is not None and stage2_proc.poll() is not None:
            break
        time.sleep(0.2)

    # Final read in case metrics were flushed just before the processes exited.
    if stage1_metrics is None:
        stage1_metrics = read_metrics_record(stage1_metrics_path, stage="stage1")
    if stage2_metrics is None:
        stage2_metrics = read_metrics_record(stage2_metrics_path, stage="stage2")

    terminate_proc(stage1_proc)
    terminate_proc(stage2_proc)
    stage1_thread.join(timeout=5)
    stage2_thread.join(timeout=5)

    if not pub_done:
        fail_with_logs(run_dir, f"publisher metrics file not found: {pub_metrics_path}\n--- pub tail ---\n{tail_text(pub_log)}")
    if stage1_metrics is None:
        fail_with_logs(run_dir, f"stage1 drava metrics not found\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    if stage2_metrics is None:
        fail_with_logs(run_dir, f"stage2 drava metrics not found\n--- stage2 tail ---\n{tail_text(stage2_log)}")
    if not stage2_final:
        fail_with_logs(run_dir, f"stage2 finalize line not found\n--- stage2 tail ---\n{tail_text(stage2_log)}")

    pub_frames = int(pub_done["frames"])
    s1_frames = int(stage1_metrics["rx_items"])
    s2_frames = int(stage2_final["frames"])
    stitched_frames = int(stage2_final["stitched"])
    if not (pub_frames == s1_frames == s2_frames == stitched_frames):
        fail_with_logs(
            run_dir,
            f"frame mismatch: publisher={pub_frames} stage1_rx={s1_frames} "
            f"stage2_rx={s2_frames} stage2_final={stitched_frames}"
        )

    row["total_frames"] = pub_frames
    row["publisher_avg_fps"] = float(pub_done["avg_fps"])
    row["publisher_time_s"] = float(pub_done["duration_s"])
    row["stage1_total_time_s"] = float(stage1_metrics["stage_total_s"])
    row["stage1_total_fps"] = float(stage1_metrics["stage_total_fps"])
    row["stage2_total_time_s"] = float(stage2_metrics["stage_total_s"])
    row["stage2_total_fps"] = (
        s2_frames / row["stage2_total_time_s"]
        if row["stage2_total_time_s"] and row["stage2_total_time_s"] > 0
        else None
    )
    row["stage2_side"] = int(stage2_final["side"])

    # Measure end-to-end from the first frame actually sent (fair vs pvaPy),
    # falling back to publisher-launch time if the marker was missed.
    e2e_start = marks.get("pub_first_frame") or marks["pub_start"]
    if e2e_start is not None and marks["stage2_final"] is not None:
        row["pipeline_e2e_s"] = marks["stage2_final"] - e2e_start

    return row


def print_table(rows):
    print("")
    print(
        "| Batch | Threads S1/S2 | Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | Stage2 Time (s) | Stage2 FPS | Pipeline E2E (s) |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['batch']} | {r['stage1_threads']}/{r['stage2_threads']} | {fmt(r['total_frames'], '{:.0f}')} | "
            f"{fmt(r['publisher_time_s'])} | {fmt(r['publisher_avg_fps'])} | "
            f"{fmt(r['stage1_total_time_s'])} | {fmt(r['stage1_total_fps'])} | "
            f"{fmt(r['stage2_total_time_s'])} | {fmt(r['stage2_total_fps'])} | "
            f"{fmt(r['pipeline_e2e_s'])} |"
        )


def main():
    args = parse_args()
    batches = [int(x.strip()) for x in args.batches.split(",") if x.strip()]
    if not batches:
        raise SystemExit("No batch sizes provided.")

    root = Path(__file__).resolve().parent
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / args.out_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    stage_config_path = (root / args.stage_config).resolve() if not Path(args.stage_config).is_absolute() else Path(
        args.stage_config)
    nats_config_path = (root / args.nats_config).resolve() if not Path(args.nats_config).is_absolute() else Path(
        args.nats_config)
    nats_url = (
            args.nats_url
            or nats_url_from_config(nats_config_path)
            or parse_transport_value(stage_config_path, "nats_url")
            or "nats://127.0.0.1:4222"
    )

    base_env = dict(os.environ)
    nats_proc = None
    nats_log_file = None

    if not args.reuse_nats:
        print("[global] starting nats-server")
        nats_proc, nats_log_file, nats_log_path = start_nats(run_dir, nats_url, nats_config_path)
        ok = wait_for_log_line(nats_log_path, "Listening for client connections", 20)
        if not ok:
            terminate_proc(nats_proc)
            if nats_log_file:
                nats_log_file.close()
            raise SystemExit(f"Failed to start nats-server. See {nats_log_path}")
        print(f"[global] nats ready ({nats_url})")
    else:
        print(f"[global] reusing existing nats ({nats_url})")

    rows = []
    try:
        try:
            for b in batches:
                for run_idx in range(1, args.runs + 1):
                    print(f"Running batch={b} run={run_idx} ...")
                    # Retry intermittent native runtime crashes (e.g. XKRT
                    # "free(): invalid size" at stage init) instead of aborting
                    # the whole sweep. A fresh process usually starts cleanly.
                    attempts = max(1, args.max_retries + 1)
                    row = None
                    last_err = None
                    for attempt in range(1, attempts + 1):
                        try:
                            row = run_one(args, base_env, run_dir, b, run_idx)
                            break
                        except RuntimeError as exc:
                            last_err = exc
                            print(f"  [retry] batch={b} run={run_idx} attempt "
                                  f"{attempt}/{attempts} failed: "
                                  f"{str(exc).splitlines()[0]}", flush=True)
                            time.sleep(2.0)
                    if row is None:
                        print(f"  [skip] batch={b} run={run_idx} failed after "
                              f"{attempts} attempts; continuing sweep.", flush=True)
                        continue
                    rows.append(row)
                    print(
                        f"  done: publisher_fps={fmt(row['publisher_avg_fps'])} "
                        f"stage1_fps={fmt(row['stage1_total_fps'])} "
                        f"stage2_fps={fmt(row['stage2_total_fps'])}"
                    )

            print_table(rows)
            out_csv = run_dir / "summary.csv"
            with open(out_csv, "w", encoding="utf-8") as f:
                f.write(
                    "batch,run,stage1_threads,stage2_threads,timeout_ms,total_frames,publisher_time_s,publisher_avg_fps,"
                    "stage1_total_time_s,stage1_total_fps,"
                    "stage2_total_time_s,stage2_total_fps,stage2_side,pipeline_e2e_s\n"
                )
                for r in rows:
                    f.write(
                        f"{r['batch']},{r['run']},{r['stage1_threads']},{r['stage2_threads']},{r['timeout_ms']},{r['total_frames']},"
                        f"{r['publisher_time_s']},{r['publisher_avg_fps']},{r['stage1_total_time_s']},"
                        f"{r['stage1_total_fps']},{r['stage2_total_time_s']},{r['stage2_total_fps']},"
                        f"{r['stage2_side']},"
                        f"{r['pipeline_e2e_s']}\n"
                    )
            print(f"\nLogs and summary written to: {run_dir}", flush=True)
        except BaseException:
            print(f"\nLogs written to: {run_dir}", flush=True)
            raise
    finally:
        if nats_proc is not None:
            print("[global] stopping nats-server")
            terminate_proc(nats_proc)
        if nats_log_file is not None:
            nats_log_file.close()


if __name__ == "__main__":
    main()
