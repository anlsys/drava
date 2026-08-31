#!/usr/bin/env python3
"""Compare GPU/CPU power-vs-time across batch sizes for TomoGAN.

Reads several power_trace_*.csv files (one per batch size) and draws a small
multi-panel figure (one panel per batch) sharing axes, so the GPU duty cycle
and the flat CPU floor can be compared across batch sizes.

Usage (from a bench_logs run dir, or with explicit files):
    python plot_tomogan_power_trace_compare.py \
        --trace 2:power_trace_b2_r1.csv \
        --trace 4:power_trace_b4_r1.csv \
        --trace 8:power_trace_b8_r1.csv \
        --trace 16:power_trace_b16_r1.csv \
        --out tomogan_power_trace_compare

Or point at a directory and let it auto-pick run 1 of each batch:
    python plot_tomogan_power_trace_compare.py --dir bench_logs/<timestamp>
"""
from __future__ import annotations

import argparse
import csv
import os
import re
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
    for s in series:
        series[s].sort(key=lambda p: p[0])
    return series


def discover(dir_path: Path) -> list[tuple[int, Path]]:
    out = []
    for p in sorted(dir_path.glob("power_trace_b*_r1.csv")):
        m = re.search(r"power_trace_b(\d+)_r1\.csv", p.name)
        if m:
            out.append((int(m.group(1)), p))
    out.sort(key=lambda x: x[0])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", action="append", default=[],
                    help="batch:path, e.g. 16:power_trace_b16_r1.csv (repeatable)")
    ap.add_argument("--dir", default=None, help="Dir with power_trace_b*_r1.csv files.")
    ap.add_argument("--out", default=None, help="Output basename.")
    ap.add_argument("--orientation", choices=["vertical", "horizontal"],
                    default="horizontal",
                    help="Panel layout: horizontal (side-by-side, shows spikes) or vertical (stacked).")
    args = ap.parse_args()

    items: list[tuple[int, Path]] = []
    for spec in args.trace:
        batch, _, path = spec.partition(":")
        items.append((int(batch), Path(path).resolve()))
    if args.dir:
        items += discover(Path(args.dir).resolve())
    items.sort(key=lambda x: x[0])
    if not items:
        raise SystemExit("No traces given. Use --trace batch:path or --dir <run_dir>.")

    out_base = (Path(args.out).resolve() if args.out
                else items[-1][1].parent / "tomogan_power_trace_compare")

    plt.rcParams.update({
        "font.size": 13, "axes.labelsize": 14, "xtick.labelsize": 12,
        "ytick.labelsize": 12, "legend.fontsize": 12, "axes.titlesize": 14,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    # Parse and compute shared axis limits across panels for fair comparison.
    parsed = []
    all_pw = []
    max_t = 0.0
    for batch, path in items:
        s = read_trace(path)
        parsed.append((batch, s))
        for src in ("gpu", "cpu"):
            pts = s.get(src, [])
            all_pw += [w for _, w in pts]
            if pts:
                max_t = max(max_t, max(t for t, _ in pts))
    max_w = max(all_pw) if all_pw else 1.0
    for batch, s in parsed:
        if "cpu" not in s or not s["cpu"]:
            print(f"[warn] batch {batch}: trace has no CPU rows. The source run "
                  "likely lacked a working CPU energy source (use "
                  "--cpu-energy-source perf and confirm perf reports Joules).")

    # Shared palette with the energy-efficiency figure: GPU green, CPU orange.
    colors = {"gpu": "#6A8F7A", "cpu": "#7D5BA6"}
    labels = {"gpu": "GPU power draw", "cpu": "CPU power draw"}

    n = len(items)
    if args.orientation == "vertical":
        # Stacked rows with a common time axis makes the runtime comparison
        # across batch sizes immediate (batch 2 runs ~30 s, batch 16 ~14 s).
        # Wide + short panels: the x-axis (time) must be long enough to show the
        # runtime differences; stack them so a common time axis lines up.
        fig, axes = plt.subplots(n, 1, figsize=(7.0, 1.25 * n + 0.7),
                                 sharex=True, sharey=True, constrained_layout=True)
        axes = [axes] if n == 1 else list(axes)
        for i, (ax, (batch, s)) in enumerate(zip(axes, parsed)):
            for src in ("gpu", "cpu"):
                if src in s:
                    xs = [t for t, _ in s[src]]
                    ys = [w for _, w in s[src]]
                    ax.plot(xs, ys, color=colors[src], linewidth=1.3,
                            label=labels[src])
            ax.set_xlim(0, max_t * 1.02)
            ax.set_ylim(0, max_w * 1.08)
            ax.grid(True, color="#E8E8E8", linewidth=0.6)
            ax.set_axisbelow(True)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            # In-panel batch label (saves vertical space vs a title per panel).
            ax.text(0.995, 0.88, f"batch {batch}", transform=ax.transAxes,
                    ha="right", va="top", fontsize=13,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none",
                              alpha=0.75))
        axes[-1].set_xlabel("Time (s)")
        fig.supylabel("Power (W)")
        # Legend above the top panel so it never overlaps the traces.
        axes[0].legend(loc="lower center", bbox_to_anchor=(0.5, 1.02),
                       frameon=False, ncol=2, handlelength=1.6,
                       columnspacing=1.6, borderpad=0.2)
    else:
        fig, axes = plt.subplots(1, n, figsize=(2.5 * n + 0.8, 2.9),
                                 sharex=True, sharey=True, constrained_layout=True)
        axes = [axes] if n == 1 else list(axes)
        for ax, (batch, s) in zip(axes, parsed):
            for src in ("gpu", "cpu"):
                if src in s:
                    xs = [t for t, _ in s[src]]
                    ys = [w for _, w in s[src]]
                    ax.plot(xs, ys, color=colors[src], linewidth=1.4,
                            label=labels[src])
            ax.set_title(f"batch {batch}")
            ax.set_xlabel("Time (s)")
            ax.set_xlim(0, max_t * 1.02)
            ax.set_ylim(0, max_w * 1.08)
            ax.grid(True, color="#E8E8E8", linewidth=0.6)
            ax.set_axisbelow(True)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
        axes[0].set_ylabel("Power (W)")
        # Legend above the panels so it never covers the GPU spikes.
        handles, lbls = axes[0].get_legend_handles_labels()
        fig.legend(handles, lbls, loc="lower center", bbox_to_anchor=(0.5, 1.0),
                   ncol=2, frameon=False, handlelength=1.6, columnspacing=1.8)
        axes[0].legend(loc="upper left", frameon=False)

    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
