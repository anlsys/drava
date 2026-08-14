#!/usr/bin/env python3
"""Two-stage pvaPy benchmark using the *supported* HPC distributor path.

Instead of a single low-level monitor (which drops stage-1 predictions under
load), stage 2 runs as N ``pvapy-hpc-consumer`` processes that the pvAccess data
distributor (``pydistributor``) load-balances, each with a large receiver queue.
We sweep the number of consumers N and, for each N, check whether the N consumers
collectively received every stage-1 prediction (loss-free coverage of all
frames) and reconstructed the scan.

Pipeline:
    publisher.py --(ptychonn:frames)--> consumer.py  (stage 1: infer + publish)
                 --(ptychonn:stage1)--> N x pvapy-hpc-consumer (distributor)
                                          -> PtychoNNStitchProcessor per consumer
                                          -> per-consumer coverage JSON
    aggregator (this script): union coverage across N -> loss-free? -> stitch

Each (N, rate) run reports:
  - n_consumers, rate_hz
  - union_frames (unique frames received across all consumers)
  - expected_frames, complete (union == expected)
  - per-consumer frame counts (load balance)
  - wall-clock of the stage-2 phase

Usage:
  python benchmark_hpc_two_stage.py --n-consumers 1,2,4,8 --rate-hz 1000 \
      --num-frames 3600 --runs 3
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROCESSOR_FILE = HERE / "pvapy_hpc_stage2_processor.py"

PUB_DONE_RE = re.compile(
    r"Done:\s+published\s+(?P<frames>\d+)\s+frames\s+in\s+(?P<time>[0-9.]+)s")
STAGE1_METRICS_RE = re.compile(
    r"rx_items=(?P<rx_items>\d+).*?expected_frames=(?P<expected>\d+)"
    r".*?missed_frames=(?P<missed>\d+)")
# Harness-side marks for a fair end-to-end time that matches Drava's
# benchmark_two_stages.py definition: first frame actually sent -> last stage-2
# consumer finalize line. This excludes consumer setup and drain-poll idle.
PUB_FIRST_FRAME_STR = "First frame sent at:"
# Printed by the processor on every processed object; the harness records the
# max time across all consumers = when stage 2 finished receiving data.
CONSUMER_OBJECT_RE = re.compile(r"\[hpc-stage2\] object processed")


def parse_args():
    p = argparse.ArgumentParser(description="pvaPy HPC distributor two-stage sweep.")
    p.add_argument("--n-consumers", default="1,2,4,8", help="Comma-separated consumer counts to sweep.")
    p.add_argument("--rate-hz", default="1000",
                   help="Comma-separated publisher rate(s) in Hz to sweep, e.g. 1000,2000,2500,3000.")
    p.add_argument("--num-frames", type=int, default=3600)
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--frame-channel", default="ptychonn:frames")
    p.add_argument("--stage1-channel", default="ptychonn:stage1")
    p.add_argument("--data-dir", default="../PtychoNN_data_partial")
    p.add_argument("--infer-batch", type=int, default=256)
    p.add_argument("--publish-chunk", type=int, default=64)
    p.add_argument("--stage1-monitor-queue", type=int, default=200000,
                   help="Client monitor queue for stage 1 (--monitor-queue). Large enough "
                        "to buffer all input frames + EOS in order so stage 1 does NOT lose "
                        "input to publisher overwrite; this isolates the stage1->stage2 "
                        "boundary the distributor is meant to fix.")
    p.add_argument("--receiver-queue-size", type=int, default=20000,
                   help="Per-consumer receiver queue (-rqs); large enough to buffer bursts.")
    p.add_argument("--distributor-group", default="ptychonn")
    p.add_argument("--distributor-updates", type=int, default=1,
                   help="Sequential updates per consumer before moving to next (-du).")
    p.add_argument("--oid-field", default="uniqueId")
    p.add_argument("--consumer-runtime-s", type=float, default=120.0)
    p.add_argument("--drain-timeout-s", type=float, default=30.0,
                   help="Max seconds to wait after stage 1 EOS for consumers to write results.")
    p.add_argument("--start-settle-s", type=float, default=3.0)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--out-dir", default="bench_logs_hpc_two_stage")
    return p.parse_args()


def stream_to_log(proc, log_path, ready_evt=None, ready_str=None, done_cb=None):
    with open(log_path, "w", encoding="utf-8") as f:
        for line in proc.stdout:
            f.write(line); f.flush()
            if ready_evt is not None and ready_str and ready_str in line:
                ready_evt.set()
            if done_cb is not None:
                done_cb(line.rstrip("\n"))


def terminate(proc, grace=3.0):
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT); proc.wait(timeout=grace)
    except Exception:
        try:
            proc.terminate(); proc.wait(timeout=grace)
        except Exception:
            proc.kill()


def run_one(args, root, run_dir, n_consumers, run_idx, rate_hz):
    tag = f"n{n_consumers}_rate{int(rate_hz)}_r{run_idx}"
    hpc_out = run_dir / f"hpc_out_{tag}"
    hpc_out.mkdir(parents=True, exist_ok=True)
    stage1_log = run_dir / f"stage1_{tag}.log"
    pub_log = run_dir / f"pub_{tag}.log"
    consumer_log = run_dir / f"consumers_{tag}.log"
    control_file = run_dir / f"start_{tag}.signal"

    env = dict(os.environ); env["PYTHONUNBUFFERED"] = "1"

    # --- stage 2: N distributor consumers via pvapy-hpc-consumer -----------
    processor_args = json.dumps({
        "out_dir": str(hpc_out),
        "expected_frames": args.num_frames,
    })
    consumer_cmd = [
        "pvapy-hpc-consumer",
        "-ic", args.stage1_channel,
        "-nc", str(n_consumers),
        "-dpn", "pydistributor",
        "-dg", args.distributor_group,
        "-du", str(args.distributor_updates),
        "-of", args.oid_field,
        "-rqs", str(args.receiver_queue_size),
        "-pf", str(PROCESSOR_FILE),
        "-pc", "PtychoNNStitchProcessor",
        "-pa", processor_args,
        "-rt", str(args.consumer_runtime_s),
        "-dc",  # disable curses screen (we capture stdout via a pipe, no TTY)
    ]
    consumer_proc = subprocess.Popen(consumer_cmd, cwd=root, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1)
    import threading
    # Record the harness-clock time of the LAST consumer finalize line so the
    # end-to-end span ends when stage 2 actually finishes stitching.
    marks = {"pub_first_frame": None, "stage2_final": None}
    def on_consumer(line):
        # Every processed-object marker advances the end time; the last one across
        # all consumers is when stage 2 finished receiving all data.
        if CONSUMER_OBJECT_RE.search(line):
            marks["stage2_final"] = time.monotonic()
    ct = threading.Thread(target=stream_to_log,
                          args=(consumer_proc, consumer_log, None, None, on_consumer),
                          daemon=True)
    ct.start()
    time.sleep(args.start_settle_s)  # let consumers subscribe to the distributor

    # --- stage 1: inference + publish predictions -------------------------
    stage1_cmd = [
        args.python, "consumer.py",
        "--input-channel", args.frame_channel,
        "--output-channel", args.stage1_channel,
        "--data-dir", args.data_dir,
        "--infer-batch", str(args.infer_batch),
        "--publish-chunk", str(args.publish_chunk),
        "--monitor-queue", str(args.stage1_monitor_queue),
        "--timeout-s", str(args.consumer_runtime_s),
    ]
    s1_ready = threading.Event()
    stage1_metrics = {}
    def on_stage1(line):
        m = STAGE1_METRICS_RE.search(line)
        if m:
            stage1_metrics.update(m.groupdict())
    stage1_proc = subprocess.Popen(stage1_cmd, cwd=root, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
    s1t = threading.Thread(target=stream_to_log,
                           args=(stage1_proc, stage1_log, s1_ready, "consumer ready:", on_stage1),
                           daemon=True)
    s1t.start()
    if not s1_ready.wait(120):
        terminate(stage1_proc); terminate(consumer_proc)
        raise RuntimeError(f"stage1 not ready; see {stage1_log}")

    # --- publisher --------------------------------------------------------
    pub_done = {}
    def on_pub(line):
        if marks["pub_first_frame"] is None and PUB_FIRST_FRAME_STR in line:
            marks["pub_first_frame"] = time.monotonic()
        m = PUB_DONE_RE.search(line)
        if m:
            pub_done.update(m.groupdict())
    pub_cmd = [
        args.python, "publisher.py", "--synthetic",
        "--channel", args.frame_channel,
        "--data-dir", args.data_dir,
        "--num-frames", str(args.num_frames),
        "--rate-hz", str(rate_hz),
        "--control-file", str(control_file),
    ]
    pub_proc = subprocess.Popen(pub_cmd, cwd=root, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
    pt = threading.Thread(target=stream_to_log, args=(pub_proc, pub_log, None, None, on_pub), daemon=True)
    pt.start()
    time.sleep(1.0)
    t_start = time.monotonic()
    control_file.touch()
    pub_proc.wait(timeout=max(args.consumer_runtime_s, 60))
    pt.join(timeout=5)

    # Stage 1 buffers all input in its monitor queue; it exits on its own AFTER
    # it has inferred every frame and forwarded EOS downstream. Wait for that
    # instead of a blind timeout so we do not kill stage 1 mid-inference.
    try:
        stage1_proc.wait(timeout=args.consumer_runtime_s)
    except subprocess.TimeoutExpired:
        terminate(stage1_proc)

    # Now that stage 1 has forwarded EOS, give consumers time to drain their
    # receiver queues and write their per-consumer result files.
    drain_deadline = time.time() + args.drain_timeout_s
    while time.time() < drain_deadline:
        results = list(glob.glob(str(hpc_out / "hpc_stage2_result_c*.json")))
        if len(results) >= n_consumers:
            break
        time.sleep(0.5)
    t_stage2 = time.monotonic() - t_start

    terminate(consumer_proc); terminate(stage1_proc)
    s1t.join(timeout=5); ct.join(timeout=5)

    # --- aggregate coverage across consumers ------------------------------
    union = set()
    per_consumer = {}
    for rf in glob.glob(str(hpc_out / "hpc_stage2_result_c*.json")):
        try:
            d = json.load(open(rf))
        except Exception:
            continue
        idx = set(d.get("received_index", []))
        per_consumer[d.get("consumer_id")] = len(idx)
        union |= idx
    expected = args.num_frames
    complete = (len(union) >= expected)
    # Stage-1 coverage (publisher->stage1 boundary): how many frames stage 1
    # actually inferred+published. If < expected, stage 1 itself dropped input.
    s1_rx = int(stage1_metrics.get("rx_items", 0)) if stage1_metrics else None
    s1_published = s1_rx  # stage 1 publishes exactly what it infers

    # Fair end-to-end time: first frame sent -> last consumer finalize. Matches
    # Drava's benchmark_two_stages.py (pipeline_e2e_s). Only meaningful when the
    # run completed and both marks were captured.
    e2e = None
    if marks["pub_first_frame"] is not None and marks["stage2_final"] is not None:
        e2e = round(marks["stage2_final"] - marks["pub_first_frame"], 3)
    pipeline_fps = round(expected / e2e, 1) if (e2e and complete) else None

    row = {
        "n_consumers": n_consumers,
        "run": run_idx,
        "rate_hz": int(rate_hz),
        "num_frames": args.num_frames,
        "publisher_time_s": float(pub_done.get("time", 0.0)) if pub_done else None,
        "stage1_rx_frames": s1_rx,
        "stage1_published_frames": s1_published,
        "union_frames": len(union),
        "expected_frames": expected,
        "complete": int(complete),
        "stage2_matches_stage1": int(s1_published is not None and len(union) >= s1_published),
        "pipeline_e2e_s": e2e,
        "pipeline_fps": pipeline_fps,
        "stage2_wall_s": round(t_stage2, 3),
        "per_consumer_frames": ";".join(str(per_consumer.get(c, 0)) for c in sorted(per_consumer)),
    }
    return row


def main():
    args = parse_args()
    counts = [int(x) for x in args.n_consumers.split(",") if x.strip()]
    rates = [float(x) for x in str(args.rate_hz).split(",") if x.strip()]
    root = Path(__file__).resolve().parent
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / args.out_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for rate in rates:
        for nc in counts:
            for r in range(1, args.runs + 1):
                print(f"Running rate={int(rate)} n_consumers={nc} run={r} ...", flush=True)
                try:
                    row = run_one(args, root, run_dir, nc, r, rate)
                except Exception as exc:
                    print(f"  [error] {exc}", flush=True)
                    continue
                rows.append(row)
                print(f"  done: stage1_rx={row['stage1_rx_frames']} "
                      f"union={row['union_frames']}/{row['expected_frames']} "
                      f"complete={row['complete']} s2==s1={row['stage2_matches_stage1']} "
                      f"e2e={row['pipeline_e2e_s']}s fps={row['pipeline_fps']} "
                      f"per_consumer=[{row['per_consumer_frames']}]", flush=True)

    if rows:
        out_csv = run_dir / "summary.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\nSummary: {out_csv}", flush=True)
    print(f"Logs: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
