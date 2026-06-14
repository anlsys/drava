#!/usr/bin/env python3
"""
Generate the Experiment 1 figure used by the evaluation subsection.

Consumes exp1_summary.csv from exp1_runtime_overhead.py and writes:

  exp1_runtime_observability.{pdf,png}

The figure is a compact systems diagnostic: end-to-end latency, dominant
runtime counters, and stage service-rate balance. Multiple runs per
(stage, batch) are averaged; standard error is drawn when n > 1.

Usage:
  python3 experiments/figures/exp1_runtime_observability/plot_exp1_runtime_observability.py \
      experiments/results/exp1_20260513_205018/exp1_summary.csv \
      --out-dir experiments/figures/exp1_runtime_observability
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "drava-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "lines.linewidth": 1.8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


C_LAT = "#D62728"
C_S1 = "#2563EB"
C_S2 = "#F59E0B"
C_E2E = "#111827"
C_GRID = "#D1D5DB"
C_TEXT = "#111827"
C_MARK = "#6B7280"
X_LABEL = "Batch size $B$ (callback = inference)"

Row = Dict[str, str]
HERE = Path(__file__).resolve().parent


def load_summary(path: Path, workload: str) -> List[Row]:
    with path.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("workload") == workload]
    if not rows:
        raise SystemExit(f"No rows for workload={workload!r} in {path}")
    return rows


def group(rows: Sequence[Row]) -> Dict[Tuple[str, int], List[Row]]:
    grouped: Dict[Tuple[str, int], List[Row]] = defaultdict(list)
    for row in rows:
        grouped[(row["stage"], int(row["batch"]))].append(row)
    return grouped


def as_float(row: Row, col: str) -> float:
    value = row.get(col)
    if value in (None, "", "None"):
        return math.nan
    return float(value)


def mean_sem(values: Iterable[float]) -> Tuple[float, float]:
    vals = [v for v in values if not math.isnan(v)]
    if not vals:
        return math.nan, 0.0
    if len(vals) == 1:
        return vals[0], 0.0
    return mean(vals), stdev(vals) / math.sqrt(len(vals))


def batches_for(grouped: Dict[Tuple[str, int], List[Row]]) -> List[int]:
    return sorted({batch for _, batch in grouped})


def input_frames(grouped: Dict[Tuple[str, int], List[Row]], batch: int) -> float:
    rows = grouped.get(("stage1", batch), [])
    if rows:
        frames, _ = mean_sem(as_float(row, "frames") for row in rows)
        return frames
    frames, _ = mean_sem(as_float(row, "frames") for (stage, b), rows in grouped.items()
                         if b == batch for row in rows)
    return frames


def latency(grouped: Dict[Tuple[str, int], List[Row]], batch: int) -> Tuple[float, float]:
    rows = grouped.get(("stage1", batch), [])
    if not rows:
        rows = [row for (stage, b), stage_rows in grouped.items() if b == batch
                for row in stage_rows]
    return mean_sem(as_float(row, "end_to_end_s") for row in rows)


def component(grouped: Dict[Tuple[str, int], List[Row]],
              stage: str,
              batch: int,
              col: str) -> Tuple[float, float]:
    return mean_sem(as_float(row, col) for row in grouped.get((stage, batch), []))


def normalized_stage_fps(grouped: Dict[Tuple[str, int], List[Row]],
                         stage: str,
                         batch: int) -> Tuple[float, float]:
    rows = grouped[(stage, batch)]
    total_input = input_frames(grouped, batch)
    values = []
    for row in rows:
        fps = as_float(row, "stage_total_fps")
        stage_items = as_float(row, "frames")
        if not math.isnan(fps) and not math.isnan(stage_items) and stage_items > 0:
            values.append(fps * total_input / stage_items)
    return mean_sem(values)


def setup_axis(ax, batches: Sequence[int], panel: str) -> None:
    ax.set_xscale("log", base=2)
    ax.set_xticks(batches)
    ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.axvline(128, color=C_MARK, linewidth=0.8, linestyle=":", zorder=0)
    ax.grid(True, axis="y", color=C_GRID, linewidth=0.6, alpha=0.75)
    ax.grid(True, axis="x", color=C_GRID, linewidth=0.4, alpha=0.35)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=C_TEXT)
    ax.text(0.02, 0.95, panel, transform=ax.transAxes, ha="left", va="top",
            fontsize=12, fontweight="bold", color=C_TEXT)


def plot_runtime_observability(grouped: Dict[Tuple[str, int], List[Row]],
                               out_dir: Path) -> None:
    batches = batches_for(grouped)
    lat = [latency(grouped, b)[0] for b in batches]
    lat_err = [latency(grouped, b)[1] for b in batches]
    s1_transport = [component(grouped, "stage1", b, "transport_lumped_s")[0]
                    for b in batches]
    s2_dispatch = [component(grouped, "stage2", b, "dispatch_overhead_s")[0]
                   for b in batches]
    s1_fps = [normalized_stage_fps(grouped, "stage1", b)[0] for b in batches]
    s1_fps_err = [normalized_stage_fps(grouped, "stage1", b)[1] for b in batches]
    s2_fps = [normalized_stage_fps(grouped, "stage2", b)[0] for b in batches]
    s2_fps_err = [normalized_stage_fps(grouped, "stage2", b)[1] for b in batches]

    fig, axes = plt.subplots(1, 3, figsize=(10.0, 2.55))

    ax = axes[0]
    ax.errorbar(batches, lat, yerr=lat_err, marker="o", markersize=4.6,
                color=C_LAT, capsize=2.5)
    ax.scatter([128], [lat[batches.index(128)]], s=58, facecolors="white",
               edgecolors=C_LAT, linewidth=1.5, zorder=4)
    ax.annotate("4.09 s", (128, lat[batches.index(128)]),
                xytext=(8, 12), textcoords="offset points", color=C_LAT,
                fontsize=9, arrowprops=dict(arrowstyle="-", color=C_LAT, lw=0.7))
    ax.set_ylabel("Pipeline latency (s)")
    ax.set_ylim(0, max(lat) * 1.18)
    setup_axis(ax, batches, "(a)")

    ax = axes[1]
    ax.plot(batches, s2_dispatch, marker="s", markersize=4.2,
            color=C_S2, label="Stage 2 dispatch")
    ax.plot(batches, s1_transport, marker="o", markersize=4.2,
            color=C_S1, label="Stage 1 output transport")
    ax.set_yscale("log")
    ax.set_ylabel("Overhead (s, log scale)")
    ax.set_ylim(0.02, 20)
    ax.legend(loc="lower left", framealpha=0.95)
    setup_axis(ax, batches, "(b)")

    ax = axes[2]
    ax.errorbar(batches, s1_fps, yerr=s1_fps_err, marker="o", markersize=4.4,
                color=C_S1, capsize=2.5, label="Stage 1 inference")
    ax.errorbar(batches, s2_fps, yerr=s2_fps_err, marker="s", markersize=4.2,
                color=C_S2, capsize=2.5, label="Stage 2 stitching")
    ax.fill_between(batches, s1_fps, s2_fps, where=[a >= b for a, b in zip(s1_fps, s2_fps)],
                    color=C_S1, alpha=0.06, interpolate=True)
    ax.set_ylabel("Throughput (frames/s)")
    ax.set_ylim(0, max(max(s1_fps), max(s2_fps)) * 1.18)
    ax.legend(loc="upper right", framealpha=0.95)
    setup_axis(ax, batches, "(c)")

    fig.supxlabel(X_LABEL, fontsize=11, y=0.11)
    fig.tight_layout(w_pad=1.2, rect=(0, 0.04, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"exp1_runtime_observability.{ext}",
                    dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Experiment 1 figure")
    parser.add_argument("summary", type=Path, help="Path to exp1_summary.csv")
    parser.add_argument("--out-dir", type=Path, default=HERE,
                        help="Directory for generated PDF and PNG figures")
    parser.add_argument("--workload", default="ptychonn", choices=("ptychonn", "tomogan"),
                        help="Workload rows to plot")
    args = parser.parse_args()

    rows = load_summary(args.summary, args.workload)
    grouped = group(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_runtime_observability(grouped, args.out_dir)
    print(f"Wrote {args.out_dir / 'exp1_runtime_observability.pdf'}")


if __name__ == "__main__":
    main()
