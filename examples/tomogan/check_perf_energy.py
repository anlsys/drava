#!/usr/bin/env python3
"""Quick standalone check that perf CPU package energy is captured + parsed.

Runs a short `perf stat -x, -I <ms> -e power/energy-pkg/ -- sleep <dur>`, prints
the raw perf stderr, then the parsed total Joules and interval power series using
the exact same parser as benchmark.py.

Usage:
    python check_perf_energy.py                 # 2s window, 200ms interval
    python check_perf_energy.py --duration 2 --interval-ms 200
    python check_perf_energy.py --event power/energy-pkg/
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

# Reuse the exact sampler/parsers from the benchmark so this test matches the run.
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("tomogan_benchmark", HERE / "benchmark.py")
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perf-command", default="perf")
    ap.add_argument("--event", default="power/energy-pkg/")
    ap.add_argument("--interval-ms", type=int, default=200)
    ap.add_argument("--duration", type=float, default=2.0)
    args = ap.parse_args()

    print(f"perf available check: "
          f"{bm.perf_energy_available(args.perf_command, args.event)}")

    sampler = bm.PerfEnergySampler(args.perf_command, args.event,
                                   interval_ms=args.interval_ms)
    if not sampler.start():
        print("FAILED: could not start perf. Is perf installed and on PATH?")
        return 1
    time.sleep(args.duration)
    joules = sampler.stop()

    print("\n===== RAW perf stderr =====")
    print(sampler.stderr_text or "<empty>")
    print("===== END RAW =====\n")

    print(f"parsed total Joules: {joules}")
    print(f"interval power samples ({len(sampler.power_samples)}): "
          f"{[(round(t, 3), round(w, 1)) for t, w in sampler.power_samples][:10]}")

    if joules is None:
        print("\nRESULT: NOT parsed. Copy the RAW block above so the format can be matched.")
        return 2
    print("\nRESULT: OK, perf CPU energy is captured and parsed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
