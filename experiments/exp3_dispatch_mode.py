#!/usr/bin/env python3
"""
Experiment 3: Serial vs Work-Stealing Dispatch
==============================================

Goal
----
Compare the two callback dispatch policies in Drava:

  * serialized:  flushed batches run inline on the I/O thread (mutex-guarded)
  * parallel:    each flushed batch is spawned as an XKRT task and stolen by
                 worker threads

Hypotheses
----------
* For light callbacks (e.g. PtychoNN Stage 2 stitching) the serialized mode
  wins at low thread counts because it avoids per-batch task-spawn cost.
* For heavy callbacks (Stage 1 GPU inference, TomoGAN) parallel dispatch
  scales with threads up to a saturation point, after which work-stealing
  contention becomes visible.
* At threads=1 the two modes should converge; the gap is the per-task spawn
  overhead.

Sweep
-----
* dispatch_mode in {serialized, parallel}
* threads       in {1, 2, 4, 8}
* workload      in {ptychonn, tomogan}
* batch         fixed (default 256 ptychonn / 16 tomogan)

Required runtime change
-----------------------
This driver depends on app.py / app_stage2.py (and tomogan/app.py) honoring
the env var DRAVA_CALLBACK_SERIALIZE (0 or 1) instead of hard-coding the
mode. That env wiring is included in the same commit.

Outputs
-------
experiments/results/exp3_<ts>/exp3_summary.csv with columns:
    workload, stage, dispatch_mode, threads, batch, run, frames,
    end_to_end_s, callback_compute_s, dispatch_overhead_s,
    stage_total_fps, cb_avg_ms, stage_avg_ms
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    LatencyDecomp,
    make_run_dir,
    parse_metrics_from_log,
    read_summary_csv,
    run_ptychonn_benchmark,
    run_tomogan_benchmark,
    write_rows,
)

DISPATCH_MODES = {
    "serialized": "1",
    "parallel": "0",
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workload", choices=["ptychonn", "tomogan", "both"], default="both")
    p.add_argument("--threads-list", default="1,2,4,8")
    p.add_argument("--modes", default="serialized,parallel",
                   help="Subset of dispatch modes to sweep.")
    p.add_argument("--ptychonn-batch", type=int, default=256)
    p.add_argument("--tomogan-batch", type=int, default=16)
    p.add_argument("--ptychonn-num-frames", type=int, default=3600)
    p.add_argument("--tomogan-num-frames", type=int, default=16)
    p.add_argument("--rate-hz", type=float, default=0.0)
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--runs", type=int, default=2)
    return p.parse_args()


def collect_ptychonn(args, run_dir: Path, mode: str, threads: int) -> list[dict]:
    sub = run_dir / f"ptychonn_{mode}_t{threads}"
    ts = run_ptychonn_benchmark(
        sub,
        batches=[args.ptychonn_batch],
        stage1_threads=threads,
        stage2_threads=threads,
        stage1_callback_batch=args.ptychonn_batch,
        stage2_callback_batch=args.ptychonn_batch,
        timeout_ms=args.timeout_ms,
        rate_hz=args.rate_hz,
        num_frames=args.ptychonn_num_frames,
        runs=args.runs,
        extra_env={"DRAVA_CALLBACK_SERIALIZE": DISPATCH_MODES[mode]},
    )
    summary = read_summary_csv(ts / "summary.csv")
    rows: list[dict] = []
    for srow in summary:
        b = int(srow["batch"])
        r = int(srow["run"])
        e2e = float(srow.get("pipeline_e2e_s") or 0.0) or None
        for stage_name, log_glob in (("stage1", f"app_stage1_b{b}_r{r}.log"),
                                     ("stage2", f"app_stage2_b{b}_r{r}.log")):
            m = parse_metrics_from_log(ts / log_glob)
            if m is None:
                continue
            d = LatencyDecomp.from_stage(m, e2e)
            rows.append({
                "workload": "ptychonn",
                "stage": stage_name,
                "dispatch_mode": mode,
                "threads": threads,
                "batch": b,
                "run": r,
                "frames": m.rx_items,
                "end_to_end_s": d.end_to_end_s,
                "callback_compute_s": d.callback_compute_s,
                "dispatch_overhead_s": d.dispatch_overhead_s,
                "stage_total_fps": m.stage_total_fps,
                "cb_avg_ms": m.cb_avg_ms,
                "stage_avg_ms": m.stage_avg_ms,
            })
    return rows


def collect_tomogan(args, run_dir: Path, mode: str, threads: int) -> list[dict]:
    sub = run_dir / f"tomogan_{mode}_t{threads}"
    ts = run_tomogan_benchmark(
        sub,
        batches=[args.tomogan_batch],
        threads=threads,
        timeout_ms=args.timeout_ms,
        rate_hz=args.rate_hz,
        num_frames=args.tomogan_num_frames,
        runs=args.runs,
        extra_env={"DRAVA_CALLBACK_SERIALIZE": DISPATCH_MODES[mode]},
    )
    summary = read_summary_csv(ts / "summary.csv")
    rows: list[dict] = []
    for srow in summary:
        b = int(srow["batch"])
        r = int(srow["run"])
        e2e = float(srow.get("pipeline_e2e_s") or 0.0) or None
        m = parse_metrics_from_log(ts / f"app_b{b}_r{r}.log")
        if m is None:
            continue
        d = LatencyDecomp.from_stage(m, e2e)
        rows.append({
            "workload": "tomogan",
            "stage": "stage1",
            "dispatch_mode": mode,
            "threads": threads,
            "batch": b,
            "run": r,
            "frames": m.rx_items,
            "end_to_end_s": d.end_to_end_s,
            "callback_compute_s": d.callback_compute_s,
            "dispatch_overhead_s": d.dispatch_overhead_s,
            "stage_total_fps": m.stage_total_fps,
            "cb_avg_ms": m.cb_avg_ms,
            "stage_avg_ms": m.stage_avg_ms,
        })
    return rows


def main():
    args = parse_args()
    run_dir = make_run_dir("exp3")
    print(f"[exp3] writing to {run_dir}")

    modes = [m.strip() for m in args.modes.split(",") if m.strip() in DISPATCH_MODES]
    threads_list = [int(t) for t in args.threads_list.split(",") if t.strip()]

    rows: list[dict] = []
    for mode in modes:
        for threads in threads_list:
            if args.workload in ("ptychonn", "both"):
                rows.extend(collect_ptychonn(args, run_dir, mode, threads))
            if args.workload in ("tomogan", "both"):
                rows.extend(collect_tomogan(args, run_dir, mode, threads))

    cols = [
        "workload", "stage", "dispatch_mode", "threads", "batch", "run", "frames",
        "end_to_end_s", "callback_compute_s", "dispatch_overhead_s",
        "stage_total_fps", "cb_avg_ms", "stage_avg_ms",
    ]
    out = run_dir / "exp3_summary.csv"
    write_rows(out, rows, cols)
    print(f"[exp3] wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
