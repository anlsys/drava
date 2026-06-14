#!/usr/bin/env python3
"""
Experiment 2: Microbatching Mechanism (Three Flush Triggers)
============================================================

Goal
----
Characterize how Drava's microbatching policy chooses between its three
flush triggers --- threshold (|P| >= B), end-of-stream (EOS), and timeout ---
and the resulting impact on tail latency (stage_max_ms) and throughput.

Sweep
-----
* publisher rate_hz   in {0 (max), 1000, 5000, 10000, 25000}
* fetch_timeout_ms    in {10, 50, 200, 1000}
* callback_batch      fixed (default 256)
* threads             fixed (4 / 4)

Workload
--------
PtychoNN two-stage pipeline. Stage 1 is GPU-bound and exposes timeout-driven
flushes when the publisher under-feeds; Stage 2 is CPU-bound stitcher and is
relatively timeout-insensitive.

Outputs
-------
experiments/results/exp2_<ts>/exp2_summary.csv with columns:
    stage, rate_hz, fetch_timeout_ms, batch, run, frames,
    stage_avg_ms, stage_max_ms, cb_avg_ms, cb_batches,
    flush_threshold_pct, flush_eos_pct, flush_timeout_pct,
    requires_runtime_change

Required runtime change for full attribution
--------------------------------------------
The C++ runtime must emit one log line per batch flush so the driver can
attribute each batch to a trigger. Suggested format:

    [drava-flush] stage=<name> reason=<threshold|eos|timeout> size=<n>

When those lines are absent the driver still records latency results and
sets requires_runtime_change=true.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    make_run_dir,
    parse_flush_triggers_from_log,
    parse_metrics_from_log,
    read_summary_csv,
    run_ptychonn_benchmark,
    write_rows,
)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rates", default="0,1000,5000,10000,25000",
                   help="publisher rate_hz values; 0 = max speed")
    p.add_argument("--timeouts", default="10,50,200,1000",
                   help="fetch_timeout_ms values")
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--stage1-threads", type=int, default=4)
    p.add_argument("--stage2-threads", type=int, default=4)
    p.add_argument("--num-frames", type=int, default=3600)
    p.add_argument("--runs", type=int, default=2)
    return p.parse_args()


def main():
    args = parse_args()
    run_dir = make_run_dir("exp2")
    print(f"[exp2] writing to {run_dir}")

    rates = [float(x) for x in args.rates.split(",") if x.strip()]
    timeouts = [int(x) for x in args.timeouts.split(",") if x.strip()]

    rows: list[dict] = []
    for rate in rates:
        for to_ms in timeouts:
            tag = f"rate{int(rate)}_to{to_ms}"
            sub = run_dir / tag
            ts = run_ptychonn_benchmark(
                sub,
                batches=[args.batch],
                stage1_threads=args.stage1_threads,
                stage2_threads=args.stage2_threads,
                stage1_callback_batch=args.batch,
                stage2_callback_batch=args.batch,
                timeout_ms=to_ms,
                rate_hz=rate,
                num_frames=args.num_frames,
                runs=args.runs,
            )
            summary = read_summary_csv(ts / "summary.csv")
            for srow in summary:
                b = int(srow["batch"])
                r = int(srow["run"])
                for stage_name, log_glob in (("stage1", f"app_stage1_b{b}_r{r}.log"),
                                             ("stage2", f"app_stage2_b{b}_r{r}.log")):
                    log_path = ts / log_glob
                    m = parse_metrics_from_log(log_path)
                    if m is None:
                        continue
                    triggers = parse_flush_triggers_from_log(log_path)
                    requires_change = triggers.total() == 0
                    if triggers.total() > 0:
                        t = triggers.total()
                        f_thr = 100.0 * triggers.threshold / t
                        f_eos = 100.0 * triggers.eos / t
                        f_to = 100.0 * triggers.timeout / t
                    else:
                        f_thr = f_eos = f_to = None
                    rows.append({
                        "stage": stage_name,
                        "rate_hz": rate,
                        "fetch_timeout_ms": to_ms,
                        "batch": b,
                        "run": r,
                        "frames": m.rx_items,
                        "stage_avg_ms": m.stage_avg_ms,
                        "stage_max_ms": m.stage_max_ms,
                        "cb_avg_ms": m.cb_avg_ms,
                        "cb_batches": m.cb_batches,
                        "flush_threshold_pct": f_thr,
                        "flush_eos_pct": f_eos,
                        "flush_timeout_pct": f_to,
                        "requires_runtime_change": "true" if requires_change else "false",
                    })

    cols = [
        "stage", "rate_hz", "fetch_timeout_ms", "batch", "run", "frames",
        "stage_avg_ms", "stage_max_ms", "cb_avg_ms", "cb_batches",
        "flush_threshold_pct", "flush_eos_pct", "flush_timeout_pct",
        "requires_runtime_change",
    ]
    out = run_dir / "exp2_summary.csv"
    write_rows(out, rows, cols)
    print(f"[exp2] wrote {len(rows)} rows -> {out}")
    if any(r["requires_runtime_change"] == "true" for r in rows):
        print("[exp2] NOTE: flush-trigger attribution missing. Add the")
        print("       [drava-flush] log line described in the docstring to")
        print("       enable threshold/eos/timeout fractions.")


if __name__ == "__main__":
    main()
