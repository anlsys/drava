#!/usr/bin/env python3
"""
Experiment 5: Lock-Free Instrumentation Overhead
================================================

Goal
----
Quantify the per-callback cost of Drava's always-on instrumentation
(rx/tx/cb/stage atomic counters and the CAS-loop max). Compare three
runtime builds against the same workload:

  * full          : default (current main); all counters and timing emitted
  * counters_only : counter increments retained, latency timing disabled
  * disabled      : all instrumentation paths compiled out

Hypotheses
----------
* Counter increments cost ~1 ns / callback on AMD EPYC under low contention;
  the visible cost should sit in the noise at threads <= 4 and grow modestly
  at threads = 8/16 due to cache-line ping-pong on hot atomics.
* Latency timing (clock_gettime per stage sample) is the dominant chunk;
  removing it (`counters_only`) should recover most of the gap to `disabled`.
* The disabled build is a useful upper bound on Drava's intrinsic cost.

Sweep
-----
* mode    in {full, counters_only, disabled}
* threads in {1, 4, 8}
* batch   fixed (default 256)

Required runtime change
-----------------------
The C++ runtime must support two compile-time flags:

  * -DDRAVA_DISABLE_METRICS=1            -> compile out all stats_* paths
  * -DDRAVA_DISABLE_METRICS_TIMING=1     -> keep counters, drop clock_gettime

Until those flags exist, this driver runs only the `full` mode and writes
placeholder rows for the other modes with requires_runtime_change=true.

Outputs
-------
experiments/results/exp5_<ts>/exp5_summary.csv with columns:
    mode, threads, batch, run, frames,
    end_to_end_s, callback_compute_s, cb_avg_ms,
    stage_avg_ms, stage_total_fps,
    per_callback_overhead_us, requires_runtime_change

`per_callback_overhead_us` is computed against the `disabled` build's
cb_avg_ms baseline; it is None when that baseline is not available.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    LatencyDecomp,
    make_run_dir,
    parse_metrics_from_log,
    read_summary_csv,
    run_ptychonn_benchmark,
    write_rows,
)

# Each mode maps to a hint for which build of the Drava .so the apps should
# load. The current build system installs to one location, so when there is
# only one variant present we silently fall back to it and mark the row.
BUILD_DIR_ENV = "DRAVA_BUILD_DIR_{mode}"
PYTHONPATH_ENV = "PYTHONPATH"


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modes", default="full,counters_only,disabled")
    p.add_argument("--threads-list", default="1,4,8")
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--num-frames", type=int, default=3600)
    p.add_argument("--rate-hz", type=float, default=0.0)
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--full-build-dir", default=os.getenv("DRAVA_BUILD_DIR_FULL", ""),
                   help="Path to PYTHONPATH entry exposing the full-build drava.so.")
    p.add_argument("--counters-only-build-dir",
                   default=os.getenv("DRAVA_BUILD_DIR_COUNTERS_ONLY", ""))
    p.add_argument("--disabled-build-dir",
                   default=os.getenv("DRAVA_BUILD_DIR_DISABLED", ""))
    return p.parse_args()


def env_for_mode(args, mode: str) -> dict[str, str]:
    base = dict(os.environ)
    pp_extra = ""
    if mode == "full" and args.full_build_dir:
        pp_extra = args.full_build_dir
    elif mode == "counters_only" and args.counters_only_build_dir:
        pp_extra = args.counters_only_build_dir
    elif mode == "disabled" and args.disabled_build_dir:
        pp_extra = args.disabled_build_dir
    if pp_extra:
        old = base.get(PYTHONPATH_ENV, "")
        base[PYTHONPATH_ENV] = f"{pp_extra}:{old}" if old else pp_extra
    return base


def collect(args, run_dir: Path, mode: str, threads: int) -> list[dict]:
    requires_change = False
    pp_dir_attr = {
        "full": args.full_build_dir,
        "counters_only": args.counters_only_build_dir,
        "disabled": args.disabled_build_dir,
    }[mode]
    if mode != "full" and not pp_dir_attr:
        # No alternative build provided. Run the default Drava .so and flag it.
        requires_change = True

    sub = run_dir / f"{mode}_t{threads}"
    extra_env = env_for_mode(args, mode)
    # Expose only the diff vs os.environ to avoid duplication noise.
    diff_env = {k: v for k, v in extra_env.items() if os.environ.get(k) != v}

    ts = run_ptychonn_benchmark(
        sub,
        batches=[args.batch],
        stage1_threads=threads,
        stage2_threads=threads,
        stage1_callback_batch=args.batch,
        stage2_callback_batch=args.batch,
        timeout_ms=args.timeout_ms,
        rate_hz=args.rate_hz,
        num_frames=args.num_frames,
        runs=args.runs,
        extra_env=diff_env or None,
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
                "mode": mode,
                "stage": stage_name,
                "threads": threads,
                "batch": b,
                "run": r,
                "frames": m.rx_items,
                "end_to_end_s": d.end_to_end_s,
                "callback_compute_s": d.callback_compute_s,
                "cb_avg_ms": m.cb_avg_ms,
                "stage_avg_ms": m.stage_avg_ms,
                "stage_total_fps": m.stage_total_fps,
                "per_callback_overhead_us": None,  # filled in post-pass
                "requires_runtime_change": "true" if requires_change else "false",
            })
    return rows


def fill_overhead(rows: list[dict]) -> None:
    """Compute per_callback_overhead_us for full and counters_only relative to
    the disabled-mode baseline at the same (stage, threads, batch)."""
    disabled = {
        (r["stage"], r["threads"], r["batch"]): r["cb_avg_ms"]
        for r in rows if r["mode"] == "disabled" and r["cb_avg_ms"] is not None
    }
    if not disabled:
        return
    for r in rows:
        if r["mode"] == "disabled":
            r["per_callback_overhead_us"] = 0.0
            continue
        key = (r["stage"], r["threads"], r["batch"])
        base = disabled.get(key)
        if base is None or r["cb_avg_ms"] is None:
            continue
        r["per_callback_overhead_us"] = max(0.0, (r["cb_avg_ms"] - base) * 1000.0)


def main():
    args = parse_args()
    run_dir = make_run_dir("exp5")
    print(f"[exp5] writing to {run_dir}")

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    threads_list = [int(t) for t in args.threads_list.split(",") if t.strip()]

    rows: list[dict] = []
    for mode in modes:
        for threads in threads_list:
            rows.extend(collect(args, run_dir, mode, threads))

    fill_overhead(rows)

    cols = [
        "mode", "stage", "threads", "batch", "run", "frames",
        "end_to_end_s", "callback_compute_s", "cb_avg_ms",
        "stage_avg_ms", "stage_total_fps",
        "per_callback_overhead_us", "requires_runtime_change",
    ]
    out = run_dir / "exp5_summary.csv"
    write_rows(out, rows, cols)
    print(f"[exp5] wrote {len(rows)} rows -> {out}")
    if any(r["requires_runtime_change"] == "true" for r in rows):
        print("[exp5] NOTE: alternative builds not provided. Pass")
        print("       --counters-only-build-dir and --disabled-build-dir")
        print("       (or the corresponding DRAVA_BUILD_DIR_* env vars)")
        print("       once the C++ flags exist.")


if __name__ == "__main__":
    main()
