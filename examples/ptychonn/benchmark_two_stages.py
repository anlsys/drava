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

PUB_DONE_RE = re.compile(
    r"Done:\s+published\s+(?P<frames>\d+)\s+frames\s+in\s+(?P<time>[0-9.]+)s\s+"
    r"\(avg_fps=(?P<fps>[0-9.]+)\)"
)
STAGE1_FINAL_RE = re.compile(
    r"\[stage1-final\]\s+frames=(?P<frames>\d+)\s+expected_frames=(?P<expected>\d+)\s+"
    r"frame0_arrival_s=(?P<arrival>[0-9.]+)\s+last_infer_done_s=(?P<done>[0-9.]+)\s+"
    r"end_to_end_latency_s=(?P<e2e>[0-9.]+)\s+infer_avg_fps=(?P<infer_fps>[0-9.]+)\s+"
    r"publish_avg_fps=(?P<publish_fps>[0-9.]+)\s+e2e_fps=(?P<e2e_fps>[0-9.]+)"
)
STAGE2_FINAL_RE = re.compile(
    r"\[stage2-final\]\s+frames=(?P<frames>\d+)\s+stitched_frames=(?P<stitched>\d+)\s+"
    r"stitch_side=(?P<side>\d+)\s+consume_avg_fps=(?P<consume_fps>[0-9.]+)\s+"
    r"stitch_time_s=(?P<stitch_s>[0-9.]+)"
)


def parse_args():
    p = argparse.ArgumentParser(description="Run PtychoNN two-stage benchmark matrix.")
    p.add_argument("--batches", default="128,256,512", help="Comma-separated stage1 infer batch sizes.")
    p.add_argument("--timeout-ms", type=int, default=500, help="DRAVA_FETCH_TIMEOUT_MS.")
    p.add_argument("--threads", type=int, default=1, help="DRAVA_THREADS for both apps.")
    p.add_argument("--xkaapi-verbose", type=int, default=4, help="XKAAPI_VERBOSE.")
    p.add_argument("--rate-hz", type=float, default=0.0, help="DRAVA_PUBLISH_RATE_HZ (<=0 means max speed).")
    p.add_argument("--duration-s", type=float, default=10.0, help="DRAVA_PUBLISH_DURATION_S.")
    p.add_argument("--runs", type=int, default=1, help="Runs per batch.")
    p.add_argument("--python", default=sys.executable, help="Python executable.")
    p.add_argument("--reuse-nats", action="store_true", help="Use existing NATS server.")
    p.add_argument("--nats-url", default="nats://127.0.0.1:4222", help="NATS URL.")
    p.add_argument("--out-dir", default="bench_logs_two_stages", help="Output dir under examples/ptychonn.")
    p.add_argument("--app-timeout-s", type=float, default=240.0, help="Wait for final lines after publisher exits.")
    p.add_argument("--input-stream", default="FRAMES", help="Publisher->Stage1 stream.")
    p.add_argument("--input-subject", default="frames.raw", help="Publisher->Stage1 subject.")
    p.add_argument("--output-stream", default="PREDICTIONS", help="Stage1->Stage2 stream.")
    p.add_argument("--output-subject", default="frames.stage1", help="Stage1->Stage2 subject.")
    p.add_argument("--stage1-durable-prefix", default="drava_stage1_bench", help="Stage1 durable prefix.")
    p.add_argument("--stage2-durable-prefix", default="drava_stage2_bench", help="Stage2 durable prefix.")
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
        "threads": args.threads,
        "timeout_ms": args.timeout_ms,
        "total_frames": None,
        "publisher_avg_fps": None,
        "publisher_time_s": None,
        "stage1_infer_fps": None,
        "stage1_publish_fps": None,
        "stage1_e2e_fps": None,
        "stage1_e2e_s": None,
        "stage2_consume_fps": None,
        "stage2_stitch_s": None,
        "stage2_side": None,
        "pipeline_e2e_s": None,
    }

    env_common = dict(base_env)
    env_common["DRAVA_TRANSPORT"] = "nats"
    env_common["NATS_URL"] = args.nats_url
    env_common["XKAAPI_VERBOSE"] = str(args.xkaapi_verbose)
    env_common["DRAVA_THREADS"] = str(args.threads)
    env_common["DRAVA_FETCH_TIMEOUT_MS"] = str(args.timeout_ms)

    env_stage1 = dict(env_common)
    env_stage1["DRAVA_STREAM"] = args.input_stream
    env_stage1["DRAVA_SUBJECT"] = args.input_subject
    env_stage1["DRAVA_DURABLE"] = f"{args.stage1_durable_prefix}_b{batch_size}_r{run_idx}"
    env_stage1["DRAVA_OUTPUT_STREAM"] = args.output_stream
    env_stage1["DRAVA_OUTPUT_SUBJECT"] = args.output_subject
    env_stage1["DRAVA_INFER_BATCH"] = str(batch_size)
    env_stage1["DRAVA_JS_FETCH_BATCH"] = str(batch_size)

    env_stage2 = dict(env_common)
    env_stage2["DRAVA_STREAM"] = args.output_stream
    env_stage2["DRAVA_SUBJECT"] = args.output_subject
    env_stage2["DRAVA_DURABLE"] = f"{args.stage2_durable_prefix}_b{batch_size}_r{run_idx}"
    env_stage2["DRAVA_JS_FETCH_BATCH"] = str(batch_size)
    env_stage2["DRAVA_LOG_EVERY"] = str(batch_size)

    env_pub = dict(env_common)
    env_pub["DRAVA_SUBJECT"] = args.input_subject
    env_pub["DRAVA_PUBLISH_RATE_HZ"] = str(args.rate_hz)
    env_pub["DRAVA_PUBLISH_SYNTHETIC"] = "1"
    env_pub["DRAVA_PUBLISH_DURATION_S"] = str(args.duration_s)

    root = Path(__file__).resolve().parent
    stage1_log = run_dir / f"app_stage1_b{batch_size}_r{run_idx}.log"
    stage2_log = run_dir / f"app_stage2_b{batch_size}_r{run_idx}.log"
    pub_log = run_dir / f"pub_b{batch_size}_r{run_idx}.log"

    stage1_ready = threading.Event()
    stage2_ready = threading.Event()
    stage1_final = {}
    stage2_final = {}
    pub_done = {}
    marks = {"pub_start": None, "stage2_final": None}

    def on_stage1_line(line: str):
        if "JetStream ready:" in line:
            stage1_ready.set()
        m = STAGE1_FINAL_RE.search(line)
        if m:
            stage1_final.update(m.groupdict())

    def on_stage2_line(line: str):
        if "JetStream ready:" in line:
            stage2_ready.set()
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
        raise RuntimeError(f"stage1 exited early\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    if stage2_proc.poll() is not None:
        raise RuntimeError(f"stage2 exited early\n--- stage2 tail ---\n{tail_text(stage2_log)}")

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

    pub_proc.wait(timeout=max(120, int(args.duration_s * 6)))
    pub_thread.join(timeout=5)

    end_wait = time.time() + args.app_timeout_s
    while time.time() < end_wait and (not stage1_final or not stage2_final):
        if stage1_proc.poll() is not None and stage2_proc.poll() is not None:
            break
        time.sleep(0.2)

    terminate_proc(stage1_proc)
    terminate_proc(stage2_proc)
    stage1_thread.join(timeout=5)
    stage2_thread.join(timeout=5)

    if not pub_done:
        raise RuntimeError(f"publisher final line not found\n--- pub tail ---\n{tail_text(pub_log)}")
    if not stage1_final:
        raise RuntimeError(f"stage1 final line not found\n--- stage1 tail ---\n{tail_text(stage1_log)}")
    if not stage2_final:
        raise RuntimeError(f"stage2 final line not found\n--- stage2 tail ---\n{tail_text(stage2_log)}")

    pub_frames = int(pub_done["frames"])
    s1_frames = int(stage1_final["frames"])
    s2_frames = int(stage2_final["frames"])
    if not (pub_frames == s1_frames == s2_frames):
        raise RuntimeError(
            f"frame mismatch: publisher={pub_frames} stage1={s1_frames} stage2={s2_frames}"
        )

    row["total_frames"] = pub_frames
    row["publisher_avg_fps"] = float(pub_done["fps"])
    row["publisher_time_s"] = float(pub_done["time"])
    row["stage1_infer_fps"] = float(stage1_final["infer_fps"])
    row["stage1_publish_fps"] = float(stage1_final["publish_fps"])
    row["stage1_e2e_fps"] = float(stage1_final["e2e_fps"])
    row["stage1_e2e_s"] = float(stage1_final["e2e"])
    row["stage2_consume_fps"] = float(stage2_final["consume_fps"])
    row["stage2_stitch_s"] = float(stage2_final["stitch_s"])
    row["stage2_side"] = int(stage2_final["side"])

    if marks["pub_start"] is not None and marks["stage2_final"] is not None:
        row["pipeline_e2e_s"] = marks["stage2_final"] - marks["pub_start"]

    return row


def print_table(rows):
    print("")
    print(
        "| Batch | Threads | Timeout (ms) | Frames | Publisher FPS | Stage1 Infer FPS | Stage1 Publish FPS | Stage1 E2E FPS | Stage2 Consume FPS | Stage2 Stitch (s) | Stage2 Side | Pipeline E2E (s) |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['batch']} | {r['threads']} | {r['timeout_ms']} | {fmt(r['total_frames'], '{:.0f}')} | "
            f"{fmt(r['publisher_avg_fps'])} | {fmt(r['stage1_infer_fps'])} | {fmt(r['stage1_publish_fps'])} | "
            f"{fmt(r['stage1_e2e_fps'])} | {fmt(r['stage2_consume_fps'])} | {fmt(r['stage2_stitch_s'])} | "
            f"{fmt(r['stage2_side'], '{:.0f}')} | {fmt(r['pipeline_e2e_s'])} |"
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
            terminate_proc(nats_proc)
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
                    f"  done: publisher_fps={fmt(row['publisher_avg_fps'])} "
                    f"stage1_infer_fps={fmt(row['stage1_infer_fps'])} "
                    f"stage2_consume_fps={fmt(row['stage2_consume_fps'])}"
                )

        print_table(rows)
        out_csv = run_dir / "summary.csv"
        with open(out_csv, "w", encoding="utf-8") as f:
            f.write(
                "batch,run,threads,timeout_ms,total_frames,publisher_avg_fps,publisher_time_s,"
                "stage1_infer_fps,stage1_publish_fps,stage1_e2e_fps,stage1_e2e_s,"
                "stage2_consume_fps,stage2_stitch_s,stage2_side,pipeline_e2e_s\n"
            )
            for r in rows:
                f.write(
                    f"{r['batch']},{r['run']},{r['threads']},{r['timeout_ms']},{r['total_frames']},"
                    f"{r['publisher_avg_fps']},{r['publisher_time_s']},{r['stage1_infer_fps']},"
                    f"{r['stage1_publish_fps']},{r['stage1_e2e_fps']},{r['stage1_e2e_s']},"
                    f"{r['stage2_consume_fps']},{r['stage2_stitch_s']},{r['stage2_side']},"
                    f"{r['pipeline_e2e_s']}\n"
                )
        print(f"\nLogs and summary written to: {run_dir}")
    finally:
        if nats_proc is not None:
            print("[global] stopping nats-server")
            terminate_proc(nats_proc)
        if nats_log_file is not None:
            nats_log_file.close()


if __name__ == "__main__":
    main()
