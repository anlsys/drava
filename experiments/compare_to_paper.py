#!/usr/bin/env python3
"""Compare a fresh benchmark run against the committed paper reference data.

The paper's per-run measurements are committed under
``experiments/figures/<experiment>/`` as CSVs. This tool reads a fresh run's
``summary.csv`` (produced by an example benchmark driver), aggregates it by the
grouping columns, and prints the percent difference from the paper reference for
the key metrics. It is a reproducibility check, not a pass/fail gate: small
differences are expected across nodes and runs.

Currently supports the TomoGAN energy experiment.

Usage:
    python experiments/compare_to_paper.py tomogan-energy path/to/summary.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REFERENCE = {
    "tomogan-energy": REPO
    / "experiments/figures/tomogan_energy/tomogan_energy_efficiency_data.csv",
}
# Metrics compared, and the group key for aggregation.
_METRICS = ("stage_fps", "gpu_energy_j_per_frame",
            "cpu_energy_j_per_frame", "total_energy_j_per_frame")
_GROUP = ("batch",)


def _read_grouped(path: Path, metrics):
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    grouped = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = tuple(r.get(k, "") for k in _GROUP)
        for m in metrics:
            v = r.get(m, "")
            if v not in ("", None):
                try:
                    grouped[key][m].append(float(v))
                except ValueError:
                    pass
    return grouped


def _mean(xs):
    return statistics.fmean(xs) if xs else float("nan")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("experiment", choices=sorted(REFERENCE),
                   help="Which paper experiment to compare against.")
    p.add_argument("summary_csv", help="Path to a fresh run's summary.csv.")
    p.add_argument("--tolerance-pct", type=float, default=15.0,
                   help="Flag metrics whose mean differs by more than this (default 15%%).")
    args = p.parse_args(argv)

    ref_path = REFERENCE[args.experiment]
    fresh_path = Path(args.summary_csv)
    if not fresh_path.exists():
        print(f"error: summary not found: {fresh_path}", file=sys.stderr)
        return 2

    ref = _read_grouped(ref_path, _METRICS)
    fresh = _read_grouped(fresh_path, _METRICS)

    print(f"Comparing {fresh_path}")
    print(f"against paper reference {ref_path.relative_to(REPO)}")
    print(f"(means per batch; flag > {args.tolerance_pct:.0f}% difference)\n")

    header = f"{'batch':>6} {'metric':<26} {'paper':>12} {'run':>12} {'diff %':>9}"
    print(header)
    print("-" * len(header))

    flagged = 0
    for key in sorted(ref, key=lambda k: [float(x) for x in k]):
        batch = key[0]
        for m in _METRICS:
            ref_mean = _mean(ref[key].get(m, []))
            run_mean = _mean(fresh.get(key, {}).get(m, []))
            if run_mean != run_mean:  # NaN: metric missing in fresh run
                print(f"{batch:>6} {m:<26} {ref_mean:>12.4f} {'n/a':>12} {'—':>9}")
                continue
            diff = (run_mean - ref_mean) / ref_mean * 100.0 if ref_mean else 0.0
            mark = "  <-- check" if abs(diff) > args.tolerance_pct else ""
            if mark:
                flagged += 1
            print(f"{batch:>6} {m:<26} {ref_mean:>12.4f} {run_mean:>12.4f} "
                  f"{diff:>+8.1f}%{mark}")

    print()
    if flagged:
        print(f"{flagged} metric(s) exceeded {args.tolerance_pct:.0f}%. Small "
              f"differences across nodes/runs are normal; large ones warrant a look.")
    else:
        print("All compared metrics within tolerance of the paper reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
