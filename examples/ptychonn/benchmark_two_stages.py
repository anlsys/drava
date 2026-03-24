#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

DRAVA_METRICS_RE = re.compile(
    r"\[drava-metrics\]\s+reason=(?P<reason>\S+)\s+rx_msgs=(?P<rx_msgs>\d+)\s+"
    r"rx_items=(?P<rx_items>\d+)\s+rx_bytes=(?P<rx_bytes>\d+)\s+tx_msgs=(?P<tx_msgs>\d+)\s+"
    r"tx_bytes=(?P<tx_bytes>\d+)\s+cb_batches=(?P<cb_batches>\d+)\s+cb_avg_ms=(?P<cb_avg_ms>[0-9.]+)\s+"
    r"stage_samples=(?P<stage_samples>\d+)\s+stage_avg_ms=(?P<stage_avg_ms>[0-9.]+)\s+"
    r"stage_max_ms=(?P<stage_max_ms>[0-9.]+)\s+rx_item_fps=(?P<rx_item_fps>[0-9.]+)\s+"
    r"tx_msg_fps=(?P<tx_msg_fps>[0-9.]+)\s+cb_total_s=(?P<cb_total_s>[0-9.]+)\s+"
    r"publish_total_s=(?P<publish_total_s>[0-9.]+)\s+compute_total_s=(?P<compute_total_s>[0-9.]+)\s+"
    r"stage_total_s=(?P<stage_total_s>[0-9.]+)\s+stage_total_fps=(?P<stage_total_fps>[0-9.]+)\s+"
    r"stage=(?P<stage>\S+)"
)
PUB_DONE_RE = re.compile(
    r"Done:\s+published\s+(?P<frames>\d+)\s+frames\s+in\s+(?P<time>[0-9.]+)s\s+"
    r"\(avg_fps=(?P<fps>[0-9.]+)\)"
)
STAGE2_FINAL_RE = re.compile(
    r"\[stage2-final\]\s+frames=(?P<frames>\d+)\s+stitched_frames=(?P<stitched>\d+)\s+"
    r"stitch_side=(?P<side>\d+)"
)


def parse_args():
    p = argparse.ArgumentParser(description="Run PtychoNN two-stage benchmark matrix.")
    p.add_argument("--batches", default="128,256,512", help="Comma-separated stage1 infer batch sizes.")
    p.add_argument("--timeout-ms", type=int, default=500, help="DRAVA_FETCH_TIMEOUT_MS.")
    p.add_argument("--threads", type=int, default=1, help="DRAVA_THREADS for both apps.")
    p.add_argument("--stage1-threads", type=int, default=None, help="Override DRAVA_THREADS for stage1.")
    p.add_argument("--stage2-threads", type=int, default=None, help="Override DRAVA_THREADS for stage2.")
    p.add_argument("--stage1-callback-batch", type=int, default=None,
                   help="Override DRAVA_CALLBACK_BATCH for stage1.")
    p.add_argument("--stage2-callback-batch", type=int, default=None,
                   help="Override DRAVA_CALLBACK_BATCH for stage2.")
    p.add_argument("--xkaapi-verbose", type=int, default=4, help="XKAAPI_VERBOSE.")
    p.add_argument("--rate-hz", type=float, default=None, help="DRAVA_PUBLISH_RATE_HZ (<=0 means max speed).")
    p.add_argument("--num-frames", type=int, default=0, help="DRAVA_PUBLISH_NUM_FRAMES. Overrides duration mode.")
    p.add_argument("--runs", type=int, default=1, help="Runs per batch.")
    p.add_argument("--python", default=sys.executable, help="Python executable.")
    p.add_argument("--reuse-nats", action="store_true", help="Use existing NATS server.")
    p.add_argument("--nats-url", default="", help="NATS URL. Defaults to stage1 ingress url from --stage-config.")
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


def start_nats(run_dir: Path, nats_url: str):
    host_port = nats_url.replace("nats://", "")
    if ":" not in host_port:
        raise RuntimeError(f"Invalid --nats-url: {nats_url}")
    host, port = host_port.rsplit(":", 1)
    cmd = ["nats-server", "-js", "-a", host, "-p", port]
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
    base_input_stream = args.input_stream
    base_input_subject = parse_stage_ingress_value(stage_config_path, "stage1", "subject") or args.input_subject
    base_output_stream = args.output_stream
    base_output_subject = args.output_subject
    nats_url = (
            args.nats_url
            or parse_stage_ingress_value(stage_config_path, "stage1", "url")
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
    stage1_threads = (
        args.stage1_threads
        if args.stage1_threads is not None
        else int(yaml_stage1_threads) if yaml_stage1_threads is not None
        else args.threads
    )
    stage2_threads = (
        args.stage2_threads
        if args.stage2_threads is not None
        else int(yaml_stage2_threads) if yaml_stage2_threads is not None
        else args.threads
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
    env_common["DRAVA_STAGE_CONFIG"] = str(stage_config_path)

    run_tag = f"{run_dir.name}_b{batch_size}_r{run_idx}"
    input_stream = f"{base_input_stream}_{run_tag}"
    input_subject = f"{base_input_subject}.{run_tag}"
    output_stream = f"{base_output_stream}_{run_tag}"
    output_subject = f"{base_output_subject}.{run_tag}"
    stage1_job_id = str(abs(hash(run_tag)) % 2147483647 or 1)

    env_stage1 = dict(env_common)
    env_stage1["DRAVA_THREADS"] = str(stage1_threads)
    env_stage1["DRAVA_DURABLE"] = f"{args.stage1_durable_prefix}_{run_tag}"
    env_stage1["DRAVA_STREAM"] = input_stream
    env_stage1["DRAVA_SUBJECT"] = input_subject
    env_stage1["DRAVA_OUTPUT_STREAM"] = output_stream
    env_stage1["DRAVA_OUTPUT_SUBJECT"] = output_subject
    env_stage1["DRAVA_INFER_BATCH"] = str(batch_size)
    env_stage1["DRAVA_CALLBACK_BATCH"] = str(stage1_callback_batch)
    env_stage1["DRAVA_STAGE_NAME"] = "stage1"
    env_stage1["STAGE1_JOB_ID"] = stage1_job_id

    env_stage2 = dict(env_common)
    env_stage2["DRAVA_THREADS"] = str(stage2_threads)
    env_stage2["DRAVA_DURABLE"] = f"{args.stage2_durable_prefix}_{run_tag}"
    env_stage2["DRAVA_STREAM"] = output_stream
    env_stage2["DRAVA_SUBJECT"] = output_subject
    env_stage2["DRAVA_CALLBACK_BATCH"] = str(stage2_callback_batch)
    env_stage2["DRAVA_STAGE_NAME"] = "stage2"

    env_pub = dict(env_common)
    env_pub["NATS_URL"] = nats_url
    env_pub["DRAVA_STREAM"] = input_stream
    env_pub["DRAVA_SUBJECT"] = input_subject
    env_pub["DRAVA_PUBLISH_RATE_HZ"] = str(
        float(args.rate_hz) if args.rate_hz is not None else float(yaml_rate_hz or 0.0)
    )
    env_pub["DRAVA_PUBLISH_SYNTHETIC"] = "1"
    if args.num_frames > 0:
        env_pub["DRAVA_PUBLISH_NUM_FRAMES"] = str(args.num_frames)
    elif yaml_num_frames is not None:
        env_pub["DRAVA_PUBLISH_NUM_FRAMES"] = str(int(yaml_num_frames))
    else:
        raise RuntimeError(
            "No publisher frame count configured. Set --num-frames or "
            "publisher.num_frames in the stage config YAML."
        )

    stage1_log = run_dir / f"app_stage1_b{batch_size}_r{run_idx}.log"
    stage2_log = run_dir / f"app_stage2_b{batch_size}_r{run_idx}.log"
    pub_log = run_dir / f"pub_b{batch_size}_r{run_idx}.log"

    stage1_ready = threading.Event()
    stage2_ready = threading.Event()
    stage1_metrics = {}
    stage2_metrics = {}
    stage2_final = {}
    pub_done = {}
    marks = {"pub_start": None, "stage2_final": None}

    def on_stage1_line(line: str):
        if "JetStream ready:" in line:
            stage1_ready.set()
        m = DRAVA_METRICS_RE.search(line)
        if m:
            gd = m.groupdict()
            if gd.get("reason") in ("rx_eos", "tx_eos"):
                stage1_metrics.update(gd)

    def on_stage2_line(line: str):
        if "JetStream ready:" in line:
            stage2_ready.set()
        m = DRAVA_METRICS_RE.search(line)
        if m:
            gd = m.groupdict()
            if gd.get("reason") in ("rx_eos", "tx_eos"):
                stage2_metrics.update(gd)
        m = STAGE2_FINAL_RE.search(line)
        if m:
            stage2_final.update(m.groupdict())
            marks["stage2_final"] = time.monotonic()

    def on_pub_line(line: str):
        m = PUB_DONE_RE.search(line)
        if m:
            pub_done.update(m.groupdict())

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

    if stage1_proc.poll() is not None:
        fail_with_logs(run_dir, f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    if stage2_proc.poll() is not None:
        fail_with_logs(run_dir, f"stage2 exited early\n--- stage2 tail ---\n{tail_text(stage2_log)}")

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

    end_wait = time.time() + effective_app_timeout_s
    while time.time() < end_wait and (
            not stage1_metrics
            or not stage2_metrics
            or not stage2_final
    ):
        if stage1_proc.poll() is not None and stage2_proc.poll() is not None:
            break
        time.sleep(0.2)

    terminate_proc(stage1_proc)
    terminate_proc(stage2_proc)
    stage1_thread.join(timeout=5)
    stage2_thread.join(timeout=5)

    if not pub_done:
        fail_with_logs(run_dir, f"publisher final line not found\n--- pub tail ---\n{tail_text(pub_log)}")
    if not stage1_metrics:
        fail_with_logs(run_dir, f"stage1 drava metrics not found\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    if not stage2_metrics:
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
    row["publisher_avg_fps"] = float(pub_done["fps"])
    row["publisher_time_s"] = float(pub_done["time"])
    row["stage1_total_time_s"] = float(stage1_metrics["stage_total_s"])
    row["stage1_total_fps"] = float(stage1_metrics["stage_total_fps"])
    row["stage2_total_time_s"] = float(stage2_metrics["stage_total_s"])
    row["stage2_total_fps"] = (
        s2_frames / row["stage2_total_time_s"]
        if row["stage2_total_time_s"] and row["stage2_total_time_s"] > 0
        else None
    )
    row["stage2_side"] = int(stage2_final["side"])

    if marks["pub_start"] is not None and marks["stage2_final"] is not None:
        row["pipeline_e2e_s"] = marks["stage2_final"] - marks["pub_start"]

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
    nats_url = (
            args.nats_url
            or parse_stage_ingress_value(stage_config_path, "stage1", "url")
            or "nats://127.0.0.1:4222"
    )

    base_env = dict(os.environ)
    nats_proc = None
    nats_log_file = None

    if not args.reuse_nats:
        print("[global] starting nats-server")
        nats_proc, nats_log_file, nats_log_path = start_nats(run_dir, nats_url)
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
                    row = run_one(args, base_env, run_dir, b, run_idx)
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
