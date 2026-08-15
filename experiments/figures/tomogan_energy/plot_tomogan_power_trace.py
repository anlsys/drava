#!/usr/bin/env python3
"""Plot GPU and CPU power (W) vs time for a single TomoGAN run.

Input: a power_trace_*.csv produced by examples/tomogan/benchmark.py with
--save-power-trace. Columns: rel_time_s, source (gpu|cpu), power_w.

Usage:
    python plot_tomogan_power_trace.py path/to/power_trace_b16_r1.csv
    python plot_tomogan_power_trace.py path/to/power_trace_b16_r1.csv --out mytrace
"""
from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[3] / ".matplotlib-cache"),
)

import matplotlib.pyplot as plt


def read_trace(path: Path) -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = defaultdict(list)
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            series[row["source"]].append((float(row["rel_time_s"]), float(row["power_w"])))
    for source in series:
        series[source].sort(key=lambda p: p[0])
    return series


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot GPU/CPU power vs time for a TomoGAN run.")
    parser.add_argument("trace_csv", help="power_trace_*.csv from benchmark.py --save-power-trace")
    parser.add_argument("--out", default=None, help="Output basename (default: alongside input).")
    args = parser.parse_args()

    trace_path = Path(args.trace_csv).resolve()
    series = read_trace(trace_path)
    if not series:
        raise SystemExit(f"No samples found in {trace_path}")

    out_base = Path(args.out).resolve() if args.out else trace_path.with_suffix("")

    plt.rcParams.update({
        "font.size": 12,
        "axes.labelsize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(3.6, 2.7), constrained_layout=True)
    # Shared palette with the energy-efficiency figure: GPU green, CPU orange.
    colors = {"gpu": "#6A8F7A", "cpu": "#7D5BA6"}
    labels = {"gpu": "GPU power draw", "cpu": "CPU power draw"}
    for source in ("gpu", "cpu"):
        if source not in series:
            continue
        xs = [t for t, _ in series[source]]
        ys = [w for _, w in series[source]]
        ax.plot(xs, ys, color=colors[source], linewidth=1.5, label=labels[source])

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Power (W)")
    ax.grid(True, color="#E0E0E0", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(loc="best", frameon=False)

    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
