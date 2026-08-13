#!/usr/bin/env python3
"""Two-stage pvaPy PtychoNN baseline benchmark.

Orchestrates the full two-stage PtychoNN pipeline entirely on pvaPy/PVA, with
no Drava or NATS in the path:

    publisher.py  --(ptychonn:frames)-->  consumer.py  (stage 1: GPU inference)
                  --(ptychonn:stage1)-->  consumer_stage2.py  (stage 2: stitch)

This mirrors Drava's ``benchmark_two_stages.py`` so the end-to-end latency and
per-stage throughput of the two runtimes can be compared on identical science
(same synthetic frame pool + seed, same Keras model, same inference batch
sweep, same overlap-add stitching).
"""
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

STAGE1_METRICS_RE = re.compile(
    r"\[pvapy-metrics\]\s+rx_items=(?P<rx_items>\d+)\s+rx_bytes=(?P<rx_bytes>\d+)\s+"
    r"expected_frames=(?P<expected_frames>\d+)\s+missed_frames=(?P<missed_frames>\d+)\s+"
    r"output_msgs=(?P<output_msgs>\d+)\s+cb_batches=(?P<cb_batches>\d+)\s+"
    r"cb_avg_ms=(?P<cb_avg_ms>[0-9.]+)\s+infer_total_s=(?P<infer_total_s>[0-9.]+)\s+"
    r"publish_total_s=(?P<publish_total_s>[0-9.]+)\s+stage_total_s=(?P<stage_total_s>[0-9.]+)\s+"
    r"stage_total_fps=(?P<stage_total_fps>[0-9.]+)\s+publish_output=(?P<publish_output>\d+)"
)
STAGE2_METRICS_RE = re.compile(
    r"\[pvapy-stage2-metrics\]\s+rx_msgs=(?P<rx_msgs>\d+)\s+rx_bytes=(?P<rx_bytes>\d+)\s+"
    r"missed_msgs=(?P<missed_msgs>\d+)\s+cb_batches=(?P<cb_batches>\d+)\s+"
    r"cb_avg_ms=(?P<cb_avg_ms>[0-9.]+)\s+stitch_total_s=(?P<stitch_total_s>[0-9.]+)\s+"
    r"stage_total_s=(?P<stage_total_s>[0-9.]+)\s+stage_total_fps=(?P<stage_total_fps>[0-9.]+)\s+"
    r"expected_frames=(?P<expected_frames>\d+)\s+stitched_frames=(?P<stitched_frames>\d+)\s+"
    r"stitch_side=(?P<stitch_side>\d+)"
)
STAGE2_FINAL_RE = re.compile(
    r"\[pvapy-stage2-final\]\s+frames=(?P<frames>\d+)\s+stitched_frames=(?P<stitched>\d+)\s+"
    r"stitch_side=(?P<side>\d+)"
)
PUB_DONE_RE = re.compile(
    r"Done:\s+published\s+(?P<frames>\d+)\s+frames\s+in\s+(?P<time>[0-9.]+)s\s+"
    r"\(avg_fps=(?P<fps>[0-9.]+)\)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a two-stage pvaPy PtychoNN baseline benchmark matrix.")
    parser.add_argument("--batches", default="128,256,512", help="Stage-1 inference batch sizes.")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--num-frames", type=int, default=3600)
    parser.add_argument("--rate-hz", type=float, default=0.0)
    parser.add_argument("--synthetic", action="store_true", default=True)
    parser.add_argument("--real-data", dest="synthetic", action="store_false")
    parser.add_argument("--data-dir", default="../PtychoNN_data_partial")
    parser.add_argument("--frame-channel", default="ptychonn:frames")
    parser.add_argument("--stage1-channel", default="ptychonn:stage1")
    parser.add_argument("--monitor-queue", type=int, default=0)
    parser.add_argument("--stage1-publish-rate-hz", type=float, default=-1.0,
                        help="Pace stage-1 prediction output (msgs/s) so the stage-2 "
                             "overwrite-record monitor can keep up. Default -1 ties it to "
                             "--rate-hz (the input publisher rate); 0 = unpaced.")
    parser.add_argument("--publish-chunk", type=int, default=0,
                        help="Stage-1 prediction chunk size (frames per output message). "
                             "0 = one message per inference batch (fewest messages, least "
                             "overwrite risk on the single-record path).")
    parser.add_argument(
        "--start-settle-s",
        type=float,
        default=2.0,
        help="Delay after both consumers are ready before releasing the publisher.",
    )
    parser.add_argument("--consumer-timeout-s", type=float, default=180.0)
    parser.add_argument("--stage2-idle-timeout-s", type=float, default=15.0,
                        help="Stage-2 finalizes best-effort if idle this long (dropped EOS).")
    parser.add_argument("--stage2-extra-wait-s", type=float, default=60.0,
                        help="Extra time to wait for stage 2 to finalize after stage 1 finishes.")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--out-dir", default="bench_logs_two_stage")
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
    stage1_log = run_dir / f"stage1_b{batch}_r{run_idx}.log"
    stage2_log = run_dir / f"stage2_b{batch}_r{run_idx}.log"
    pub_log = run_dir / f"publisher_b{batch}_r{run_idx}.log"
    control_file = run_dir / f"start_b{batch}_r{run_idx}.signal"

    row: dict[str, object] = {
        "batch": batch,
        "run": run_idx,
        "num_frames": args.num_frames,
        "monitor_queue": args.monitor_queue,
        "publisher_time_s": None,
        "publisher_avg_fps": None,
        "stage1_rx_items": None,
        "stage1_expected_frames": None,
        "stage1_missed_frames": None,
        "stage1_total_s": None,
        "stage1_total_fps": None,
        "stage1_infer_total_s": None,
        "stage2_rx_msgs": None,
        "stage2_missed_msgs": None,
        "stage2_stitch_total_s": None,
        "stage2_total_s": None,
        "stage2_total_fps": None,
        "stage2_stitched_frames": None,
        "stage2_side": None,
        "pipeline_e2e_s": None,
    }

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"

    marks: dict[str, float | None] = {"pub_start": None, "stage2_final": None}

    # ------------------------------------------------------------------ pub
    pub_ready = threading.Event()
    pub_done: dict[str, str] = {}

    def on_pub_line(line: str) -> None:
        if "PVA input channel ready" in line:
            pub_ready.set()
        match = PUB_DONE_RE.search(line)
        if match:
            pub_done.update(match.groupdict())

    pub_cmd = [
        args.python, "publisher.py",
        "--channel", args.frame_channel,
        "--data-dir", args.data_dir,
        "--num-frames", str(args.num_frames),
        "--rate-hz", str(args.rate_hz),
        "--control-file", str(control_file),
    ]
    if args.synthetic:
        pub_cmd.append("--synthetic")

    pub_proc = subprocess.Popen(
        pub_cmd, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log, on_pub_line), daemon=True)
    pub_thread.start()

    if not pub_ready.wait(30):
        terminate_proc(pub_proc)
        raise RuntimeError(f"publisher did not become ready.\n--- publisher log ---\n{tail_text(pub_log)}")

    # -------------------------------------------------------------- stage 2
    stage2_ready = threading.Event()
    stage2_metrics: dict[str, str] = {}
    stage2_final: dict[str, str] = {}

    def on_stage2_line(line: str) -> None:
        if "consumer ready:" in line:
            stage2_ready.set()
        m = STAGE2_METRICS_RE.search(line)
        if m:
            stage2_metrics.update(m.groupdict())
        mf = STAGE2_FINAL_RE.search(line)
        if mf:
            stage2_final.update(mf.groupdict())
            marks["stage2_final"] = time.monotonic()

    stage2_cmd = [
        args.python, "consumer_stage2.py",
        "--input-channel", args.stage1_channel,
        "--monitor-queue", str(args.monitor_queue),
        "--timeout-s", str(args.consumer_timeout_s),
        "--idle-timeout-s", str(args.stage2_idle_timeout_s),
    ]
    stage2_proc = subprocess.Popen(
        stage2_cmd, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    stage2_thread = threading.Thread(target=stream_lines, args=(stage2_proc, stage2_log, on_stage2_line), daemon=True)
    stage2_thread.start()

    # -------------------------------------------------------------- stage 1
    stage1_ready = threading.Event()
    stage1_metrics: dict[str, str] = {}

    def on_stage1_line(line: str) -> None:
        if "consumer ready:" in line:
            stage1_ready.set()
        m = STAGE1_METRICS_RE.search(line)
        if m:
            stage1_metrics.update(m.groupdict())

    # Default (-1): tie stage-1 output pacing to the input publisher rate so the
    # stage-2 overwrite-record monitor sees updates at the same cadence the
    # single-stage baseline uses (where PvaPy is loss-free up to ~2 kHz).
    stage1_publish_rate_hz = (
        args.rate_hz if args.stage1_publish_rate_hz < 0 else args.stage1_publish_rate_hz
    )

    stage1_cmd = [
        args.python, "consumer.py",
        "--input-channel", args.frame_channel,
        "--output-channel", args.stage1_channel,
        "--data-dir", args.data_dir,
        "--infer-batch", str(batch),
        "--monitor-queue", str(args.monitor_queue),
        "--timeout-s", str(args.consumer_timeout_s),
        "--publish-rate-hz", str(stage1_publish_rate_hz),
        # 0 -> largest chunk that keeps a message near ~2 MB (64 frames), which
        # cuts the message count vs the 16-frame default while staying well under
        # pvaPy's payload limits. Fewer messages => fewer overwrite races.
        "--publish-chunk", str(args.publish_chunk if args.publish_chunk > 0 else min(batch, 64)),
    ]
    stage1_proc = subprocess.Popen(
        stage1_cmd, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    stage1_thread = threading.Thread(target=stream_lines, args=(stage1_proc, stage1_log, on_stage1_line), daemon=True)
    stage1_thread.start()

    if not stage1_ready.wait(120) or not stage2_ready.wait(120):
        terminate_proc(stage1_proc)
        terminate_proc(stage2_proc)
        terminate_proc(pub_proc)
        raise RuntimeError(
            "consumers did not become ready.\n"
            f"--- stage1 log ---\n{tail_text(stage1_log)}\n"
            f"--- stage2 log ---\n{tail_text(stage2_log)}"
        )

    if args.start_settle_s > 0:
        time.sleep(args.start_settle_s)

    marks["pub_start"] = time.monotonic()
    control_file.touch()

    pub_proc.wait(timeout=max(args.consumer_timeout_s, 60.0))
    pub_thread.join(timeout=5)

    # Wait for stage 1 metrics and stage 2 finalize.
    stage1_proc.wait(timeout=args.consumer_timeout_s)
    stage1_thread.join(timeout=5)

    end_wait = time.time() + args.stage2_extra_wait_s
    while time.time() < end_wait and (not stage2_metrics or not stage2_final):
        if stage2_proc.poll() is not None:
            break
        time.sleep(0.2)

    terminate_proc(stage2_proc)
    stage2_thread.join(timeout=5)

    # ------------------------------------------------------------- validate
    if not pub_done:
        raise RuntimeError(f"publisher final line not found.\n--- publisher log ---\n{tail_text(pub_log)}")
    if not stage1_metrics:
        raise RuntimeError(f"stage1 metrics not found.\n--- stage1 log ---\n{tail_text(stage1_log)}")
    if not stage2_metrics:
        raise RuntimeError(f"stage2 metrics not found.\n--- stage2 log ---\n{tail_text(stage2_log)}")
    if not stage2_final:
        raise RuntimeError(f"stage2 finalize line not found.\n--- stage2 log ---\n{tail_text(stage2_log)}")

    pub_frames = int(pub_done["frames"])
    s1_rx = int(stage1_metrics["rx_items"])
    s1_missed = int(stage1_metrics["missed_frames"])
    s2_stitched = int(stage2_final["stitched"])

    row["publisher_time_s"] = float(pub_done["time"])
    row["publisher_avg_fps"] = float(pub_done["fps"])
    row["stage1_rx_items"] = s1_rx
    row["stage1_expected_frames"] = int(stage1_metrics["expected_frames"])
    row["stage1_missed_frames"] = s1_missed
    row["stage1_total_s"] = float(stage1_metrics["stage_total_s"])
    row["stage1_total_fps"] = float(stage1_metrics["stage_total_fps"])
    row["stage1_infer_total_s"] = float(stage1_metrics["infer_total_s"])
    row["stage2_rx_msgs"] = int(stage2_metrics["rx_msgs"])
    row["stage2_missed_msgs"] = int(stage2_metrics["missed_msgs"])
    row["stage2_stitch_total_s"] = float(stage2_metrics["stitch_total_s"])
    row["stage2_total_s"] = float(stage2_metrics["stage_total_s"])
    row["stage2_total_fps"] = float(stage2_metrics["stage_total_fps"])
    row["stage2_stitched_frames"] = s2_stitched
    row["stage2_side"] = int(stage2_final["side"])

    if marks["pub_start"] is not None and marks["stage2_final"] is not None:
        row["pipeline_e2e_s"] = marks["stage2_final"] - marks["pub_start"]

    # Warn (do not hard-fail) on frame loss so lossy operating points still
    # produce a row for the loss/overrun discussion in the paper.
    if s1_missed or s1_rx != pub_frames:
        print(
            f"[warn] stage1 frame loss: publisher={pub_frames} stage1_rx={s1_rx} "
            f"stage1_missed={s1_missed} (simple PvaServer record path overwrites "
            "under load; use --rate-hz pacing or the queued path for a loss-free point).",
            flush=True,
        )

    return row


def print_table(rows: list[dict[str, object]]) -> None:
    print("")
    print(
        "| Batch | Frames | Pub FPS | S1 FPS | S1 Missed | S2 FPS | Stitched | Side | E2E (s) |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        e2e = row["pipeline_e2e_s"]
        print(
            f"| {row['batch']} | {row['stage1_rx_items']} | "
            f"{row['publisher_avg_fps']:.2f} | {row['stage1_total_fps']:.2f} | "
            f"{row['stage1_missed_frames']} | {row['stage2_total_fps']:.2f} | "
            f"{row['stage2_stitched_frames']} | {row['stage2_side']} | "
            f"{'n/a' if e2e is None else f'{e2e:.2f}'} |"
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
                print(f"Running two-stage pvaPy baseline batch={batch} run={run_idx} ...", flush=True)
                row = run_one(args, root, run_dir, batch, run_idx)
                rows.append(row)
                e2e = row["pipeline_e2e_s"]
                print(
                    f"  done: publisher_avg_fps={row['publisher_avg_fps']:.2f} "
                    f"stage1_fps={row['stage1_total_fps']:.2f} "
                    f"stage2_fps={row['stage2_total_fps']:.2f} "
                    f"e2e={'n/a' if e2e is None else f'{e2e:.2f}s'}",
                    flush=True,
                )
    finally:
        print(f"\nLogs written to: {run_dir}", flush=True)

    print_table(rows)
    out_csv = run_dir / "summary.csv"
    fieldnames = list(rows[0].keys()) if rows else []
    if fieldnames:
        with open(out_csv, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Summary written to: {out_csv}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
