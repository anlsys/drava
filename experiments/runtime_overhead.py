#!/usr/bin/env python3
"""
Experiment 1: Runtime Overhead Characterization
================================================

Goal
----
Quantify how Drava's runtime overhead (transport + microbatching wait +
dispatch + publish) scales relative to the user callback's compute time
across batch sizes, and report the share of end-to-end latency attributable
to the runtime vs the user code.

Workloads
---------
* PtychoNN two-stage pipeline (Stage 1 GPU inference + Stage 2 CPU stitching)
* TomoGAN single-stage GPU denoising (separate sweep, optional)

Sweep
-----
* infer_batch (== callback_batch) over {32, 64, 128, 256, 512}
* threads fixed at the baseline-best configuration
* publisher rate = 0 (max speed) so the runtime is the sole pacer
* num_frames fixed (default 3600 for PtychoNN, 16 for TomoGAN)

Outputs
-------
* experiments/results/exp1_<ts>/exp1_summary.csv with columns:
    workload, batch, runs, frames,
    end_to_end_s, callback_compute_s, publish_s, microbatching_wait_s,
    dispatch_overhead_s, transport_lumped_s,
    runtime_overhead_pct, stage_total_fps, cb_avg_ms

Required runtime changes: NONE. Uses only existing [drava-metrics] counters.
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


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workload", choices=["ptychonn", "tomogan", "both"], default="ptychonn")
    p.add_argument("--batches", default="32,64,128,256,512",
                   help="Comma-separated infer/callback batch sizes.")
    p.add_argument("--ptychonn-stage1-threads", type=int, default=4)
    p.add_argument("--ptychonn-stage2-threads", type=int, default=4)
    p.add_argument("--tomogan-threads", type=int, default=4)
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--rate-hz", type=int, default=0)
    p.add_argument("--ptychonn-num-frames", type=int, default=10000)
    p.add_argument("--tomogan-num-frames", type=int, default=16)
    p.add_argument("--runs", type=int, default=3)
    return p.parse_args()


def collect_ptychonn(args, run_dir: Path) -> list[dict]:
    batches = [int(b) for b in args.batches.split(",") if b.strip()]
    bench_dir = run_dir / "ptychonn_bench"
    # benchmark_two_stages.py applies one stage{1,2}_callback_batch to the whole
    # invocation, so we run it once per batch to keep callback_batch == infer_batch.
    rows: list[dict] = []
    for b in batches:
        sub = bench_dir / f"b{b}"
        ts = run_ptychonn_benchmark(
            sub,
            batches=[b],
            stage1_threads=args.ptychonn_stage1_threads,
            stage2_threads=args.ptychonn_stage2_threads,
            stage1_callback_batch=b,
            stage2_callback_batch=b,
            timeout_ms=args.timeout_ms,
            rate_hz=args.rate_hz,
            num_frames=args.ptychonn_num_frames,
            runs=args.runs,
        )
        summary = read_summary_csv(ts / "summary.csv")
        for srow in summary:
            # Re-derive per-stage decomposition from the app log (more reliable than CSV).
            # benchmark_two_stages.py log filenames: app_stage{1,2}_b{b}_r{r}.log
            r = int(srow["run"])
            for stage_name, log_glob in (("stage1", f"app_stage1_b{b}_r{r}.log"),
                                         ("stage2", f"app_stage2_b{b}_r{r}.log")):
                log_path = ts / log_glob
                m = parse_metrics_from_log(log_path)
                e2e = float(srow.get("pipeline_e2e_s") or 0.0) or None
                if m is None:
                    rows.append({
                        "workload": "ptychonn",
                        "stage": stage_name,
                        "batch": b,
                        "run": r,
                        "frames": int(srow.get("total_frames") or 0),
                        "end_to_end_s": e2e,
                        "callback_compute_s": None,
                        "publish_s": None,
                        "microbatching_wait_s": None,
                        "dispatch_overhead_s": None,
                        "transport_lumped_s": None,
                        "runtime_overhead_pct": None,
                        "stage_total_fps": None,
                        "cb_avg_ms": None,
                    })
                    continue
                d = LatencyDecomp.from_stage(m, e2e)
                runtime_overhead_s = sum(
                    x for x in (d.transport_lumped_s, d.microbatching_wait_s,
                                d.dispatch_overhead_s, d.publish_s) if x is not None
                )
                runtime_pct = (
                    100.0 * runtime_overhead_s / d.end_to_end_s
                    if d.end_to_end_s and d.end_to_end_s > 0 else None
                )
                rows.append({
                    "workload": "ptychonn",
                    "stage": stage_name,
                    "batch": b,
                    "run": r,
                    "frames": m.rx_items,
                    "end_to_end_s": d.end_to_end_s,
                    "callback_compute_s": d.callback_compute_s,
                    "publish_s": d.publish_s,
                    "microbatching_wait_s": d.microbatching_wait_s,
                    "dispatch_overhead_s": d.dispatch_overhead_s,
                    "transport_lumped_s": d.transport_lumped_s,
                    "runtime_overhead_pct": runtime_pct,
                    "stage_total_fps": m.stage_total_fps,
                    "cb_avg_ms": m.cb_avg_ms,
                })
    return rows


def collect_tomogan(args, run_dir: Path) -> list[dict]:
    batches = [int(b) for b in args.batches.split(",") if b.strip()]
    bench_dir = run_dir / "tomogan_bench"
    ts = run_tomogan_benchmark(
        bench_dir,
        batches=batches,
        threads=args.tomogan_threads,
        timeout_ms=args.timeout_ms,
        rate_hz=args.rate_hz,
        num_frames=args.tomogan_num_frames,
        runs=args.runs,
    )
    summary = read_summary_csv(ts / "summary.csv")
    rows: list[dict] = []
    for srow in summary:
        b = int(srow["batch"])
        r = int(srow["run"])
        log_path = ts / f"app_b{b}_r{r}.log"
        m = parse_metrics_from_log(log_path)
        e2e = float(srow.get("pipeline_e2e_s") or 0.0) or None
        if m is None:
            continue
        d = LatencyDecomp.from_stage(m, e2e)
        runtime_overhead_s = sum(
            x for x in (d.transport_lumped_s, d.microbatching_wait_s,
                        d.dispatch_overhead_s, d.publish_s) if x is not None
        )
        runtime_pct = (
            100.0 * runtime_overhead_s / d.end_to_end_s
            if d.end_to_end_s and d.end_to_end_s > 0 else None
        )
        rows.append({
            "workload": "tomogan",
            "stage": "stage1",
            "batch": b,
            "run": r,
            "frames": m.rx_items,
            "end_to_end_s": d.end_to_end_s,
            "callback_compute_s": d.callback_compute_s,
            "publish_s": d.publish_s,
            "microbatching_wait_s": d.microbatching_wait_s,
            "dispatch_overhead_s": d.dispatch_overhead_s,
            "transport_lumped_s": d.transport_lumped_s,
            "runtime_overhead_pct": runtime_pct,
            "stage_total_fps": m.stage_total_fps,
            "cb_avg_ms": m.cb_avg_ms,
        })
    return rows


def main():
    args = parse_args()
    run_dir = make_run_dir("exp1")
    print(f"[exp1] writing to {run_dir}")

    rows: list[dict] = []
    if args.workload in ("ptychonn", "both"):
        rows.extend(collect_ptychonn(args, run_dir))
    if args.workload in ("tomogan", "both"):
        rows.extend(collect_tomogan(args, run_dir))

    cols = [
        "workload", "stage", "batch", "run", "frames",
        "end_to_end_s", "callback_compute_s", "publish_s",
        "microbatching_wait_s", "dispatch_overhead_s", "transport_lumped_s",
        "runtime_overhead_pct", "stage_total_fps", "cb_avg_ms",
    ]
    out = run_dir / "exp1_summary.csv"
    write_rows(out, rows, cols)
    print(f"[exp1] wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
