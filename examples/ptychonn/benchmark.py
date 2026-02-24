#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import queue
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

APP_FINAL_RE = re.compile(
    r"\[final\]\s+frames=(?P<frames>\d+)\s+expected_frames=(?P<expected>\d+)\s+"
    r"frame0_arrival_s=(?P<arrival>[0-9.]+)\s+frame(?P<done_n>\d+)_done_s=(?P<done>[0-9.]+)\s+"
    r"end_to_end_latency_s=(?P<e2e>[0-9.]+)\s+final_wall_avg_fps=(?P<fps>[0-9.]+)"
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
    p.add_argument("--rate-hz", type=float, default=0.0,
                   help="DRAVA_PUBLISH_RATE_HZ (<=0 means max speed).")
    p.add_argument("--duration-s", type=float, default=30.0,
                   help="DRAVA_PUBLISH_DURATION_S.")
    p.add_argument("--runs", type=int, default=1,
                   help="Runs per batch size.")
    p.add_argument("--python", default=sys.executable,
                   help="Python executable to use.")
    p.add_argument("--reuse-nats", action="store_true",
                   help="Use existing NATS server instead of launching one.")
    p.add_argument("--nats-url", default="nats://127.0.0.1:4222",
                   help="NATS URL.")
    p.add_argument("--out-dir", default="bench_logs",
                   help="Output directory under examples/ptychonn.")
    p.add_argument("--app-timeout-s", type=float, default=120.0,
                   help="Max wait for app final line after publisher exits.")
    return p.parse_args()


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
        "drava_frames": None,
        "drava_avg_fps": None,
        "drava_e2e_s": None,
        "gpu_avg_pct": None,
    }

    env = dict(base_env)
    env["DRAVA_TRANSPORT"] = "nats"
    env["NATS_URL"] = args.nats_url
    env["XKAAPI_VERBOSE"] = str(args.xkaapi_verbose)
    env["DRAVA_THREADS"] = str(args.threads)
    env["DRAVA_INFER_BATCH"] = str(batch_size)
    env["DRAVA_JS_FETCH_BATCH"] = str(batch_size)
    env["DRAVA_FETCH_TIMEOUT_MS"] = str(args.timeout_ms)
    env["DRAVA_PUBLISH_RATE_HZ"] = str(args.rate_hz)
    env["DRAVA_PUBLISH_SYNTHETIC"] = "1"
    env["DRAVA_PUBLISH_DURATION_S"] = str(args.duration_s)

    app_log = run_dir / f"app_b{batch_size}_r{run_idx}.log"
    pub_log = run_dir / f"pub_b{batch_size}_r{run_idx}.log"

    app_final = {}
    app_ready = threading.Event()
    timing_marks = {"infer_start_monotonic": None, "final_monotonic": None}

    def on_app_line(line: str):
        if "JetStream ready:" in line:
            app_ready.set()
        if timing_marks["infer_start_monotonic"] is None and "[frames]=" in line:
            timing_marks["infer_start_monotonic"] = time.monotonic()
        m = APP_FINAL_RE.search(line)
        if m:
            app_final.update(m.groupdict())
            timing_marks["final_monotonic"] = time.monotonic()

    print(f"[batch={batch_size} run={run_idx}] starting app.py")
    app_proc = subprocess.Popen(
        [args.python, "app.py"],
        cwd=Path(__file__).resolve().parent,
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
        cwd=Path(__file__).resolve().parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log, on_pub_line), daemon=True)
    pub_thread.start()

    pub_proc.wait(timeout=max(120, int(args.duration_s * 4)))
    pub_thread.join(timeout=5)
    print(f"[batch={batch_size} run={run_idx}] publisher finished")

    end_wait = time.time() + args.app_timeout_s
    print(f"[batch={batch_size} run={run_idx}] waiting for app final (timeout={args.app_timeout_s}s)")
    while time.time() < end_wait and not app_final:
        if app_proc.poll() is not None:
            break
        time.sleep(0.2)

    gpu_stop.set()
    gpu_thread.join(timeout=2)

    terminate_proc(app_proc, "app")
    app_thread.join(timeout=5)
    if app_final:
        print(f"[batch={batch_size} run={run_idx}] app final received")
    else:
        print(f"[batch={batch_size} run={run_idx}] app final not found")

    if pub_done:
        row["publisher_frames"] = int(pub_done["frames"])
        row["publisher_time_s"] = float(pub_done["time"])
        row["publisher_avg_fps"] = float(pub_done["fps"])
        row["total_frames"] = row["publisher_frames"]
    else:
        raise RuntimeError(f"[batch={batch_size} run={run_idx}] failed to parse publisher final line")

    if app_final:
        row["drava_frames"] = int(app_final["frames"])
        row["drava_e2e_s"] = float(app_final["e2e"])
        row["drava_avg_fps"] = float(app_final["fps"])
        if row["total_frames"] is None:
            row["total_frames"] = row["drava_frames"]
    else:
        raise RuntimeError(f"[batch={batch_size} run={run_idx}] app final line not found")

    if row["publisher_frames"] != row["drava_frames"]:
        raise RuntimeError(
            f"[batch={batch_size} run={run_idx}] frame mismatch: "
            f"publisher={row['publisher_frames']} drava={row['drava_frames']}"
        )

    if gpu_samples:
        t0 = timing_marks["infer_start_monotonic"]
        t1 = timing_marks["final_monotonic"]
        if t0 is not None and t1 is not None and t1 >= t0:
            window = [v for (t, v) in gpu_samples if t0 <= t <= t1]
            if window:
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
        "| Batch | Threads | Timeout (ms) | Total Frames | Publisher Avg FPS | Drava Avg FPS | Publisher Time (s) | Drava E2E (s) | GPU Avg (%) |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['batch']} | {r['threads']} | {r['timeout_ms']} | "
            f"{fmt(r['total_frames'], '{:.0f}')} | {fmt(r['publisher_avg_fps'])} | "
            f"{fmt(r['drava_avg_fps'])} | {fmt(r['publisher_time_s'])} | "
            f"{fmt(r['drava_e2e_s'])} | {fmt(r['gpu_avg_pct'])} |"
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

    base_env = dict(os.environ)
    nats_proc = None
    nats_log_file = None

    if not args.reuse_nats:
        print("[global] starting nats-server")
        nats_proc, nats_log_file, nats_log_path = start_nats(run_dir, args.nats_url)
        ok = wait_for_log_line(nats_log_path, "Listening for client connections", 20)
        if not ok:
            terminate_proc(nats_proc, "nats")
            if nats_log_file:
                nats_log_file.close()
            raise SystemExit(f"Failed to start nats-server. See {nats_log_path}")
        print(f"[global] nats ready ({args.nats_url})")
    else:
        print(f"[global] reusing existing nats ({args.nats_url})")

    rows = []
    try:
        for b in batches:
            for run_idx in range(1, args.runs + 1):
                print(f"Running batch={b} run={run_idx} ...")
                row = run_one(args, base_env, run_dir, b, run_idx)
                rows.append(row)
                print(
                    f"  done: publisher_avg_fps={fmt(row['publisher_avg_fps'])} "
                    f"drava_avg_fps={fmt(row['drava_avg_fps'])}"
                )
    finally:
        if nats_proc is not None:
            print("[global] stopping nats-server")
            terminate_proc(nats_proc, "nats")
        if nats_log_file is not None:
            nats_log_file.close()

    print_table(rows)
    out_csv = run_dir / "summary.csv"
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write(
            "batch,threads,timeout_ms,total_frames,publisher_avg_fps,drava_avg_fps,publisher_time_s,drava_e2e_s,gpu_avg_pct\n")
        for r in rows:
            f.write(
                f"{r['batch']},{r['threads']},{r['timeout_ms']},{r['total_frames']},"
                f"{r['publisher_avg_fps']},{r['drava_avg_fps']},{r['publisher_time_s']},{r['drava_e2e_s']},"
                f"{r['gpu_avg_pct']}\n"
            )
    print(f"\nLogs and summary written to: {run_dir}")


if __name__ == "__main__":
    main()
