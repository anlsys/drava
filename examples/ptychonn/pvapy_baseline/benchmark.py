#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

METRICS_RE = re.compile(
    r"\[pvapy-metrics\]\s+rx_items=(?P<rx_items>\d+)\s+rx_bytes=(?P<rx_bytes>\d+)\s+"
    r"expected_frames=(?P<expected_frames>\d+)\s+missed_frames=(?P<missed_frames>\d+)\s+"
    r"output_msgs=(?P<output_msgs>\d+)\s+cb_batches=(?P<cb_batches>\d+)\s+"
    r"cb_avg_ms=(?P<cb_avg_ms>[0-9.]+)\s+infer_total_s=(?P<infer_total_s>[0-9.]+)\s+"
    r"publish_total_s=(?P<publish_total_s>[0-9.]+)\s+stage_total_s=(?P<stage_total_s>[0-9.]+)\s+"
    r"stage_total_fps=(?P<stage_total_fps>[0-9.]+)\s+publish_output=(?P<publish_output>\d+)"
)
PUB_DONE_RE = re.compile(
    r"Done:\s+published\s+(?P<frames>\d+)\s+frames\s+in\s+(?P<time>[0-9.]+)s\s+"
    r"\(avg_fps=(?P<fps>[0-9.]+)\)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a pvaPy PtychoNN baseline benchmark matrix.")
    parser.add_argument("--batches", default="128,256,512,1024")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--num-frames", type=int, default=3600)
    parser.add_argument("--rate-hz", type=float, default=0.0)
    parser.add_argument("--synthetic", action="store_true", default=True)
    parser.add_argument("--real-data", dest="synthetic", action="store_false")
    parser.add_argument("--data-dir", default="../PtychoNN_data_partial")
    parser.add_argument("--channel", default="ptychonn:frames")
    parser.add_argument("--output-channel", default="ptychonn:stage1")
    parser.add_argument("--monitor-queue", type=int, default=0)
    parser.add_argument("--consumer-timeout-s", type=float, default=180.0)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--out-dir", default="bench_logs")
    parser.add_argument("--no-publish-output", dest="publish_output", action="store_false")
    parser.set_defaults(publish_output=True)
    return parser.parse_args()


def stream_lines(proc: subprocess.Popen, log_path: Path, line_cb=None) -> None:
    with open(log_path, "w", encoding="utf-8") as handle:
        assert proc.stdout is not None
        for line in proc.stdout:
            handle.write(line)
            handle.flush()
            if line_cb is not None:
                line_cb(line.rstrip("\n"))


def tail_text(path: Path, n: int = 40) -> str:
    if not path.exists():
        return "<no log file>"
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:])


def terminate_proc(proc: subprocess.Popen, grace_s: float = 3.0) -> None:
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


def run_one(args: argparse.Namespace, root: Path, run_dir: Path, batch: int, run_idx: int) -> dict[str, object]:
    app_log = run_dir / f"consumer_b{batch}_r{run_idx}.log"
    pub_log = run_dir / f"publisher_b{batch}_r{run_idx}.log"
    control_file = run_dir / f"start_b{batch}_r{run_idx}.signal"

    row: dict[str, object] = {
        "batch": batch,
        "run": run_idx,
        "num_frames": args.num_frames,
        "monitor_queue": args.monitor_queue,
        "publisher_time_s": None,
        "publisher_avg_fps": None,
        "rx_items": None,
        "expected_frames": None,
        "missed_frames": None,
        "output_msgs": None,
        "stage_total_s": None,
        "stage_total_fps": None,
        "infer_total_s": None,
        "publish_total_s": None,
    }

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"

    pub_ready = threading.Event()
    pub_done: dict[str, str] = {}

    def on_pub_line(line: str) -> None:
        if "PVA input channel ready" in line:
            pub_ready.set()
        match = PUB_DONE_RE.search(line)
        if match:
            pub_done.update(match.groupdict())

    pub_cmd = [
        args.python,
        "publisher.py",
        "--channel",
        args.channel,
        "--data-dir",
        args.data_dir,
        "--num-frames",
        str(args.num_frames),
        "--rate-hz",
        str(args.rate_hz),
        "--control-file",
        str(control_file),
    ]
    if args.synthetic:
        pub_cmd.append("--synthetic")

    pub_proc = subprocess.Popen(
        pub_cmd,
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log, on_pub_line), daemon=True)
    pub_thread.start()

    if not pub_ready.wait(30):
        terminate_proc(pub_proc)
        raise RuntimeError(f"publisher did not become ready.\n--- publisher log ---\n{tail_text(pub_log)}")

    metrics: dict[str, str] = {}
    consumer_ready = threading.Event()

    def on_app_line(line: str) -> None:
        if "consumer ready:" in line:
            consumer_ready.set()
        match = METRICS_RE.search(line)
        if match:
            metrics.update(match.groupdict())

    consumer_cmd = [
        args.python,
        "consumer.py",
        "--input-channel",
        args.channel,
        "--output-channel",
        args.output_channel,
        "--data-dir",
        args.data_dir,
        "--infer-batch",
        str(batch),
        "--monitor-queue",
        str(args.monitor_queue),
        "--timeout-s",
        str(args.consumer_timeout_s),
    ]
    if not args.publish_output:
        consumer_cmd.append("--no-publish-output")

    consumer_proc = subprocess.Popen(
        consumer_cmd,
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    consumer_thread = threading.Thread(target=stream_lines, args=(consumer_proc, app_log, on_app_line), daemon=True)
    consumer_thread.start()

    if not consumer_ready.wait(120):
        terminate_proc(consumer_proc)
        terminate_proc(pub_proc)
        raise RuntimeError(f"consumer did not become ready.\n--- consumer log ---\n{tail_text(app_log)}")

    control_file.touch()
    pub_proc.wait(timeout=max(args.consumer_timeout_s, 60.0))
    pub_thread.join(timeout=5)
    consumer_proc.wait(timeout=args.consumer_timeout_s)
    consumer_thread.join(timeout=5)

    if pub_proc.returncode != 0:
        raise RuntimeError(f"publisher failed with rc={pub_proc.returncode}\n--- publisher log ---\n{tail_text(pub_log)}")
    if not pub_done:
        raise RuntimeError(f"publisher final line not found.\n--- publisher log ---\n{tail_text(pub_log)}")
    if not metrics:
        if consumer_proc.returncode not in (0, 2):
            raise RuntimeError(
                f"consumer failed with rc={consumer_proc.returncode}\n--- consumer log ---\n{tail_text(app_log)}"
            )
        raise RuntimeError(f"consumer metrics not found.\n--- consumer log ---\n{tail_text(app_log)}")
    if consumer_proc.returncode not in (0, 2):
        print(
            f"[warn] consumer exited with rc={consumer_proc.returncode} after emitting metrics; "
            "continuing with parsed metrics",
            flush=True,
        )

    row["publisher_time_s"] = float(pub_done["time"])
    row["publisher_avg_fps"] = float(pub_done["fps"])
    for int_key in ("rx_items", "expected_frames", "missed_frames", "output_msgs"):
        row[int_key] = int(metrics[int_key])
    for float_key in ("stage_total_s", "stage_total_fps", "infer_total_s", "publish_total_s"):
        row[float_key] = float(metrics[float_key])
    if row["expected_frames"] and row["rx_items"] != row["expected_frames"]:
        raise RuntimeError(
            "pvaPy monitor lost frame updates: "
            f"received={row['rx_items']} expected={row['expected_frames']} "
            f"missed={row['missed_frames']} publisher_avg_fps={row['publisher_avg_fps']:.2f}. "
            "The simple PvaServer record path overwrites the current PV value at this rate. "
            "Use a lower --rate-hz for a loss-free model baseline, or use the pvaPy HPC "
            "queued/distributor path for max-rate transport comparison.\n"
            f"--- consumer log ---\n{tail_text(app_log)}"
        )
    return row


def print_table(rows: list[dict[str, object]]) -> None:
    print("")
    print("| Batch | Frames | Pub FPS | Stage FPS | Missed | Stage Time (s) | Infer (s) | Publish (s) |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        print(
            f"| {row['batch']} | {row['rx_items']} | {row['publisher_avg_fps']:.2f} | "
            f"{row['stage_total_fps']:.2f} | {row['missed_frames']} | {row['stage_total_s']:.2f} | "
            f"{row['infer_total_s']:.2f} | {row['publish_total_s']:.2f} |"
        )


def main() -> int:
    args = parse_args()
    batches = [int(item.strip()) for item in args.batches.split(",") if item.strip()]
    if not batches:
        raise SystemExit("No batch sizes provided.")
    if args.runs <= 0:
        raise SystemExit("--runs must be > 0")

    root = Path(__file__).resolve().parent
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / args.out_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    try:
        for batch in batches:
            for run_idx in range(1, args.runs + 1):
                print(f"Running pvaPy baseline batch={batch} run={run_idx} ...", flush=True)
                row = run_one(args, root, run_dir, batch, run_idx)
                rows.append(row)
                print(
                    f"  done: publisher_avg_fps={row['publisher_avg_fps']:.2f} "
                    f"stage1_fps={row['stage_total_fps']:.2f} missed={row['missed_frames']}",
                    flush=True,
                )
    finally:
        print(f"\nLogs written to: {run_dir}", flush=True)

    print_table(rows)
    out_csv = run_dir / "summary.csv"
    fieldnames = [
        "batch",
        "run",
        "num_frames",
        "monitor_queue",
        "publisher_time_s",
        "publisher_avg_fps",
        "rx_items",
        "expected_frames",
        "missed_frames",
        "output_msgs",
        "stage_total_s",
        "stage_total_fps",
        "infer_total_s",
        "publish_total_s",
    ]
    with open(out_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Summary written to: {out_csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
