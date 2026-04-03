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


def parse_args():
    p = argparse.ArgumentParser(description="Run PtychoNN benchmark matrix.")
    p.add_argument("--batches", default="128,256,512,1024",
                   help="Comma-separated infer batch sizes.")
    p.add_argument("--timeout-ms", type=int, default=500,
                   help="DRAVA_FETCH_TIMEOUT_MS.")
    p.add_argument("--threads", type=int, default=2,
                   help="DRAVA_THREADS for app.")
    p.add_argument("--xkaapi-verbose", type=int, default=4,
                   help="XKAAPI_VERBOSE for app runtime.")
    p.add_argument("--rate-hz", type=float, default=None,
                   help="DRAVA_PUBLISH_RATE_HZ (<=0 means max speed).")
    p.add_argument("--num-frames", type=int, default=0,
                   help="DRAVA_PUBLISH_NUM_FRAMES. Overrides YAML.")
    p.add_argument("--runs", type=int, default=1,
                   help="Runs per batch size.")
    p.add_argument("--python", default=sys.executable,
                   help="Python executable to use.")
    p.add_argument("--reuse-nats", action="store_true",
                   help="Use existing NATS server instead of launching one.")
    p.add_argument("--nats-url", default="",
                   help="NATS URL. Defaults to transport.nats_url from --stage-config.")
    p.add_argument("--stage-config", default="pipeline.yaml",
                   help="Stage config YAML path.")
    p.add_argument("--out-dir", default="bench_logs",
                   help="Output directory under examples/ptychonn.")
    p.add_argument("--app-timeout-s", type=float, default=None,
                   help="Max wait for Drava metrics after publisher exits.")
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


def gpu_sampler(stop_evt: threading.Event, out_list):
    cmd = ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"]
    while not stop_evt.is_set():
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=2, check=False)
            if r.returncode == 0:
                vals = []
                for ln in r.stdout.splitlines():
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        vals.append(float(ln))
                    except ValueError:
                        pass
                if vals:
                    out_list.append((time.monotonic(), sum(vals) / len(vals)))
        except Exception:
            pass
        stop_evt.wait(1.0)


def terminate_proc(proc: subprocess.Popen, name: str, grace_s=3.0):
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


def run_one(args, base_env, run_dir: Path, batch_size: int, run_idx: int):
    row = {
        "batch": batch_size,
        "run": run_idx,
        "threads": args.threads,
        "timeout_ms": args.timeout_ms,
        "total_frames": None,
        "publisher_frames": None,
        "publisher_time_s": None,
        "publisher_avg_fps": None,
        "stage1_frames": None,
        "stage1_total_time_s": None,
        "stage1_total_fps": None,
        "stage1_compute_time_s": None,
        "stage1_publish_time_s": None,
        "gpu_avg_pct": None,
    }

    root = Path(__file__).resolve().parent
    stage_config_path = (root / args.stage_config).resolve() if not Path(args.stage_config).is_absolute() else Path(
        args.stage_config)
    input_subject = parse_stage_ingress_value(stage_config_path, "stage1", "subject") or "frames.raw"
    nats_url = (
            args.nats_url
            or parse_transport_value(stage_config_path, "nats_url")
            or "nats://127.0.0.1:4222"
    )
    yaml_num_frames = parse_publisher_value(stage_config_path, "num_frames")
    yaml_rate_hz = parse_publisher_value(stage_config_path, "rate_hz")
    yaml_app_timeout_s = parse_section_value(stage_config_path, "benchmark", "app_timeout_s")
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

    env = dict(base_env)
    env["XKAAPI_VERBOSE"] = str(args.xkaapi_verbose)
    env["DRAVA_THREADS"] = str(args.threads)
    env["DRAVA_STAGE_CONFIG"] = str(stage_config_path)
    env["DRAVA_STAGE_NAME"] = "stage1"
    env["DRAVA_INFER_BATCH"] = str(batch_size)
    env["DRAVA_CALLBACK_BATCH"] = str(batch_size)
    env["DRAVA_PUBLISH_RATE_HZ"] = str(
        float(args.rate_hz) if args.rate_hz is not None else float(yaml_rate_hz or 0.0)
    )
    env["DRAVA_PUBLISH_SYNTHETIC"] = "1"
    if args.num_frames > 0:
        env["DRAVA_PUBLISH_NUM_FRAMES"] = str(args.num_frames)
    elif yaml_num_frames is not None:
        env["DRAVA_PUBLISH_NUM_FRAMES"] = str(int(yaml_num_frames))
    else:
        raise RuntimeError(
            "No publisher frame count configured. Set --num-frames or "
            "publisher.num_frames in the stage config YAML."
        )
    env["DRAVA_STAGE_NAME"] = "stage1"

    app_log = run_dir / f"app_b{batch_size}_r{run_idx}.log"
    pub_log = run_dir / f"pub_b{batch_size}_r{run_idx}.log"

    app_metrics = {}
    app_ready = threading.Event()
    timing_marks = {"infer_start_monotonic": None, "final_monotonic": None}

    def on_app_line(line: str):
        if "JetStream ready:" in line:
            app_ready.set()
        if timing_marks["infer_start_monotonic"] is None and "drava_transport" in line:
            timing_marks["infer_start_monotonic"] = time.monotonic()
        m = DRAVA_METRICS_RE.search(line)
        if m:
            gd = m.groupdict()
            if gd.get("reason") in ("rx_eos", "tx_eos"):
                app_metrics.update(gd)
            timing_marks["final_monotonic"] = time.monotonic()

    print(f"[batch={batch_size} run={run_idx}] starting app.py")
    app_proc = subprocess.Popen(
        [args.python, "app.py"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    app_thread = threading.Thread(target=stream_lines, args=(app_proc, app_log, on_app_line), daemon=True)
    app_thread.start()

    ready_deadline = time.time() + 120
    saw_ready_log = False
    while time.time() < ready_deadline:
        if app_ready.is_set():
            saw_ready_log = True
            break
        if app_proc.poll() is not None:
            break
        time.sleep(0.2)

    if app_proc.poll() is not None:
        out = tail_text(app_log)
        raise RuntimeError(
            f"[batch={batch_size} run={run_idx}] app exited before publisher start.\n"
            f"--- app log tail ---\n{out}"
        )

    if saw_ready_log:
        print(f"[batch={batch_size} run={run_idx}] app ready")
    else:
        print(f"[batch={batch_size} run={run_idx}] app ready-log not seen; proceeding")

    gpu_samples = []
    gpu_stop = threading.Event()
    gpu_thread = threading.Thread(target=gpu_sampler, args=(gpu_stop, gpu_samples), daemon=True)
    gpu_thread.start()

    pub_done = {}

    def on_pub_line(line: str):
        m = PUB_DONE_RE.search(line)
        if m:
            pub_done.update(m.groupdict())

    print(f"[batch={batch_size} run={run_idx}] starting publisher_jetstream.py")
    pub_proc = subprocess.Popen(
        [args.python, "publisher_jetstream.py"],
        cwd=root,
        env=dict(env, NATS_URL=nats_url, DRAVA_SUBJECT=input_subject),
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
    print(f"[batch={batch_size} run={run_idx}] publisher finished")

    end_wait = time.time() + effective_app_timeout_s
    print(f"[batch={batch_size} run={run_idx}] waiting for drava metrics (timeout={effective_app_timeout_s}s)")
    while time.time() < end_wait and not app_metrics:
        if app_proc.poll() is not None:
            break
        time.sleep(0.2)

    gpu_stop.set()
    gpu_thread.join(timeout=2)

    terminate_proc(app_proc, "app")
    app_thread.join(timeout=5)
    if app_metrics:
        print(f"[batch={batch_size} run={run_idx}] drava metrics received")
    else:
        print(f"[batch={batch_size} run={run_idx}] drava metrics not found")

    if pub_done:
        row["publisher_frames"] = int(pub_done["frames"])
        row["publisher_time_s"] = float(pub_done["time"])
        row["publisher_avg_fps"] = float(pub_done["fps"])
        row["total_frames"] = row["publisher_frames"]
    else:
        raise RuntimeError(f"[batch={batch_size} run={run_idx}] failed to parse publisher final line")

    if app_metrics:
        row["stage1_frames"] = int(app_metrics["rx_items"])
        row["stage1_total_time_s"] = float(app_metrics["stage_total_s"])
        row["stage1_total_fps"] = float(app_metrics["stage_total_fps"])
        if row["total_frames"] is None:
            row["total_frames"] = row["stage1_frames"]
    else:
        raise RuntimeError(f"[batch={batch_size} run={run_idx}] drava metrics line not found")

    if row["publisher_frames"] != row["stage1_frames"]:
        raise RuntimeError(
            f"[batch={batch_size} run={run_idx}] frame mismatch: "
            f"publisher={row['publisher_frames']} stage1={row['stage1_frames']}"
        )

    if gpu_samples:
        t0 = timing_marks["infer_start_monotonic"]
        t1 = timing_marks["final_monotonic"]
        if t0 is not None and t1 is not None and t1 >= t0:
            window = [v for (t, v) in gpu_samples if t0 <= t <= t1]
            if window:
                print(f"GPU Usage: {window}")
                row["gpu_avg_pct"] = sum(window) / len(window)
            else:
                row["gpu_avg_pct"] = sum(v for (_, v) in gpu_samples) / len(gpu_samples)
        else:
            row["gpu_avg_pct"] = sum(v for (_, v) in gpu_samples) / len(gpu_samples)

    return row


def fmt(x, f="{:.2f}"):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return f.format(x)


def print_table(rows):
    print("")
    print(
        "| Batch | Threads | Total Frames | Publisher Time (s) | Publisher FPS | Stage1 Time (s) | Stage1 FPS | GPU Avg (%) |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['batch']} | {r['threads']} | "
            f"{fmt(r['total_frames'], '{:.0f}')} | {fmt(r['publisher_time_s'])} | "
            f"{fmt(r['publisher_avg_fps'])} | {fmt(r['stage1_total_time_s'])} | "
            f"{fmt(r['stage1_total_fps'])} | "
            f"{fmt(r['gpu_avg_pct'])} |"
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
            or parse_transport_value(stage_config_path, "nats_url")
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
            terminate_proc(nats_proc, "nats")
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
                        f"  done: publisher_avg_fps={fmt(row['publisher_avg_fps'])} "
                        f"stage1_fps={fmt(row['stage1_total_fps'])}"
                    )

            print_table(rows)
            out_csv = run_dir / "summary.csv"
            with open(out_csv, "w", encoding="utf-8") as f:
                f.write(
                    "batch,threads,timeout_ms,total_frames,publisher_time_s,publisher_avg_fps,"
                    "stage1_total_time_s,stage1_total_fps,stage1_compute_time_s,stage1_publish_time_s,gpu_avg_pct\n")
                for r in rows:
                    f.write(
                        f"{r['batch']},{r['threads']},{r['timeout_ms']},{r['total_frames']},"
                        f"{r['publisher_time_s']},{r['publisher_avg_fps']},{r['stage1_total_time_s']},"
                        f"{r['stage1_total_fps']},{r['stage1_compute_time_s']},{r['stage1_publish_time_s']},"
                        f"{r['gpu_avg_pct']}\n"
                    )
            print(f"\nLogs and summary written to: {run_dir}")
        except BaseException:
            print(f"\nLogs written to: {run_dir}")
            raise
    finally:
        if nats_proc is not None:
            print("[global] stopping nats-server")
            terminate_proc(nats_proc, "nats")
        if nats_log_file is not None:
            nats_log_file.close()


if __name__ == "__main__":
    main()
