#!/usr/bin/env python3
"""
Generate figures for Experiment 1: Runtime Overhead Characterization.

Consumes the exp1_summary.csv produced by exp1_runtime_overhead.py
(one row per (stage, batch, run)) and emits three figures:

  1. exp1_overhead_stacked.{pdf,png}  Per-stage non-callback runtime cost,
                                      stacked by component, vs. batch size.
  2. exp1_crossover.{pdf,png}         Stage 1 transport cost vs. Stage 2
                                      dispatch cost on shared log-log axes.
  3. exp1_e2e_decomp.{pdf,png}        Pipeline E2E latency vs. summed
                                      per-stage non-callback overhead.

Multiple runs per (stage, batch) are averaged; the std-error is drawn as
an errorbar when n > 1.

Usage:
  python visualize_exp1.py <exp1_summary.csv> [--out-dir figures/exp1/] \
                                              [--workload ptychonn|tomogan]
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ── Colors (kept consistent with sibling visualize_*.py scripts) ─────────────

C_TRANSPORT = "#3B82F6"     # blue
C_DISPATCH = "#F59E0B"      # amber
C_PUBLISH = "#10B981"       # green
C_MBWAIT = "#8B5CF6"        # purple
C_E2E = "#EF4444"           # red
C_GREY = "#9CA3AF"

COMPONENTS: List[Tuple[str, str, str]] = [
    # (csv_col, legend_label, color)
    ("transport_lumped_s",  "Transport",         C_TRANSPORT),
    ("dispatch_overhead_s", "Dispatch",          C_DISPATCH),
    ("publish_s",           "Publish",           C_PUBLISH),
    ("microbatching_wait_s", "Microbatch wait",  C_MBWAIT),
]

# Threshold below which a component is treated as zero for plotting.
EPS_S = 1e-6


# ── Data loading ─────────────────────────────────────────────────────────────

def load_summary(path: Path, workload: str) -> List[Dict[str, str]]:
    with path.open() as f:
        rows = [r for r in csv.DictReader(f) if r.get("workload") == workload]
    if not rows:
        raise SystemExit(f"No rows for workload={workload!r} in {path}")
    return rows


def group_by_stage_batch(rows: Sequence[Dict[str, str]]) \
        -> Dict[str, Dict[int, List[Dict[str, str]]]]:
    out: Dict[str, Dict[int, List[Dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[r["stage"]][int(r["batch"])].append(r)
    return out


def agg(rows: Sequence[Dict[str, str]], col: str) -> Tuple[float, float]:
    """Return (mean, sem) over a list of rows for a numeric column."""
    vals: List[float] = []
    for r in rows:
        v = r.get(col)
        if v in (None, "", "None"):
            continue
        try:
            vals.append(float(v))
        except ValueError:
            continue
    if not vals:
        return float("nan"), 0.0
    arr = np.asarray(vals, dtype=float)
    mean = float(arr.mean())
    sem = float(arr.std(ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0
    return mean, sem


# ── 1. Stacked overhead bars ─────────────────────────────────────────────────

def plot_overhead_stacked(grouped: Dict[str, Dict[int, List[Dict[str, str]]]],
                          out_dir: Path) -> None:
    stages = [s for s in ("stage1", "stage2") if s in grouped]
    fig, axes = plt.subplots(1, len(stages), figsize=(5.6 * len(stages), 4.2),
                             sharey=False)
    if len(stages) == 1:
        axes = [axes]

    for ax, stage in zip(axes, stages):
        per_batch = grouped[stage]
        batches = sorted(per_batch)
        x = np.arange(len(batches))

        # Stack components.
        bottom = np.zeros(len(batches))
        for col, label, color in COMPONENTS:
            means = np.asarray([agg(per_batch[b], col)[0] for b in batches])
            means = np.where(means < EPS_S, 0.0, means)
            ax.bar(x, means, bottom=bottom, color=color, edgecolor="white",
                   linewidth=0.6, label=label)
            bottom += means

        # Total annotation on top of each bar.
        for i, total in enumerate(bottom):
            if total > 0:
                ax.text(i, total + 0.15, f"{total:.2f}s", ha="center",
                        fontsize=8, color="#374151")

        ax.set_xticks(x)
        ax.set_xticklabels([str(b) for b in batches])
        ax.set_xlabel("Inference batch size $B$", fontsize=11)
        ax.set_ylabel("Non-callback runtime cost (s)", fontsize=11)
        ax.set_title({"stage1": "Stage 1 (inference)",
                      "stage2": "Stage 2 (stitching)"}[stage],
                     fontsize=12, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)

    # Single shared legend (top-right of last axis).
    axes[-1].legend(fontsize=9, loc="upper left", framealpha=0.95)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"exp1_overhead_stacked.{ext}",
                    dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [overhead_stacked] {out_dir / 'exp1_overhead_stacked.pdf'}")


# ── 2. Crossover line plot ───────────────────────────────────────────────────

def plot_crossover(grouped: Dict[str, Dict[int, List[Dict[str, str]]]],
                   out_dir: Path) -> None:
    if "stage1" not in grouped or "stage2" not in grouped:
        print("  [crossover] need both stage1 and stage2 rows; skipping")
        return

    s1 = grouped["stage1"]
    s2 = grouped["stage2"]
    batches = sorted(set(s1) & set(s2))
    if not batches:
        print("  [crossover] no shared batch sizes; skipping")
        return

    x = np.asarray(batches, dtype=float)
    s1_tr_m = np.asarray([agg(s1[b], "transport_lumped_s")[0] for b in batches])
    s1_tr_e = np.asarray([agg(s1[b], "transport_lumped_s")[1] for b in batches])
    s2_ds_m = np.asarray([agg(s2[b], "dispatch_overhead_s")[0] for b in batches])
    s2_ds_e = np.asarray([agg(s2[b], "dispatch_overhead_s")[1] for b in batches])

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.errorbar(x, s1_tr_m, yerr=s1_tr_e, color=C_TRANSPORT, marker="o",
                linewidth=2, markersize=7, capsize=3,
                label="Stage 1 transport")
    ax.errorbar(x, s2_ds_m, yerr=s2_ds_e, color=C_DISPATCH, marker="s",
                linewidth=2, markersize=7, capsize=3,
                label="Stage 2 dispatch")

    # Estimate crossover (linear interp in log space between sign-changes).
    diff = s1_tr_m - s2_ds_m
    cross_x = None
    for i in range(len(batches) - 1):
        if diff[i] * diff[i + 1] < 0:
            # Linear interp in log(B).
            lb0, lb1 = np.log(x[i]), np.log(x[i + 1])
            d0, d1 = diff[i], diff[i + 1]
            cross_lb = lb0 - d0 * (lb1 - lb0) / (d1 - d0)
            cross_x = float(np.exp(cross_lb))
            # y at crossover: average of the two lines at that point in log space.
            ly0_s1 = np.log(max(s1_tr_m[i], EPS_S))
            ly1_s1 = np.log(max(s1_tr_m[i + 1], EPS_S))
            cross_y = float(np.exp(ly0_s1 + (cross_lb - lb0) / (lb1 - lb0) * (ly1_s1 - ly0_s1)))
            ax.axvline(cross_x, color=C_GREY, linestyle="--", linewidth=1, alpha=0.7)
            ax.annotate(f"crossover\n$B \\approx {cross_x:.0f}$",
                        (cross_x, cross_y),
                        xytext=(12, 18), textcoords="offset points",
                        fontsize=9, color="#374151",
                        arrowprops=dict(arrowstyle="-", color=C_GREY, lw=0.8))
            break

    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_xlabel("Inference batch size $B$", fontsize=11)
    ax.set_ylabel("Runtime cost (s, log)", fontsize=11)
    ax.set_title("Transport vs. dispatch cost crossover",
                 fontsize=12, fontweight="bold")
    ax.grid(alpha=0.3, which="both")
    ax.set_axisbelow(True)
    ax.legend(fontsize=10, loc="lower left", framealpha=0.95)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"exp1_crossover.{ext}",
                    dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [crossover] {out_dir / 'exp1_crossover.pdf'}")


# ── 3. E2E vs summed overhead ───────────────────────────────────────────────

def plot_e2e_decomp(grouped: Dict[str, Dict[int, List[Dict[str, str]]]],
                    out_dir: Path) -> None:
    if "stage1" not in grouped or "stage2" not in grouped:
        print("  [e2e_decomp] need both stages; skipping")
        return

    s1 = grouped["stage1"]
    s2 = grouped["stage2"]
    batches = sorted(set(s1) & set(s2))
    x = np.asarray(batches, dtype=float)

    e2e_m = np.asarray([agg(s1[b], "end_to_end_s")[0] for b in batches])

    def overhead_sum(per_batch_rows):
        total = 0.0
        for col, _, _ in COMPONENTS:
            v, _ = agg(per_batch_rows, col)
            if not np.isnan(v):
                total += v
        return total

    s1_rt = np.asarray([overhead_sum(s1[b]) for b in batches])
    s2_rt = np.asarray([overhead_sum(s2[b]) for b in batches])

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(x, e2e_m, color=C_E2E, marker="o", linewidth=2.4, markersize=8,
            label=r"Pipeline $T_{e2e}$", zorder=4)
    ax.plot(x, s1_rt, color=C_TRANSPORT, marker="^", linewidth=1.8,
            markersize=7, linestyle="--",
            label="Stage 1 non-callback runtime")
    ax.plot(x, s2_rt, color=C_DISPATCH, marker="v", linewidth=1.8,
            markersize=7, linestyle="--",
            label="Stage 2 non-callback runtime")

    # Mark the empirical minimum of E2E.
    i_min = int(np.argmin(e2e_m))
    ax.scatter([x[i_min]], [e2e_m[i_min]], s=140, facecolors="none",
               edgecolors=C_E2E, linewidth=2, zorder=5)
    ax.annotate(f"min $T_{{e2e}} = {e2e_m[i_min]:.2f}$ s\nat $B = {int(x[i_min])}$",
                (x[i_min], e2e_m[i_min]),
                xytext=(14, -32), textcoords="offset points",
                fontsize=9, color=C_E2E, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=C_E2E, lw=0.8))

    ax.set_xscale("log", base=2)
    ax.set_xticks(x)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_xlabel("Inference batch size $B$", fontsize=11)
    ax.set_ylabel("Time (s)", fontsize=11)
    ax.set_title("Pipeline latency tracks summed runtime overhead",
                 fontsize=12, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(fontsize=10, loc="upper left", framealpha=0.95)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"exp1_e2e_decomp.{ext}",
                    dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [e2e_decomp] {out_dir / 'exp1_e2e_decomp.pdf'}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Visualize Experiment 1 results")
    p.add_argument("summary", type=Path, help="Path to exp1_summary.csv")
    p.add_argument("--out-dir", type=Path, default=Path("figures/exp1"),
                   help="Output directory for figures")
    p.add_argument("--workload", default="ptychonn",
                   choices=("ptychonn", "tomogan"),
                   help="Which workload to plot (rows are filtered)")
    args = p.parse_args()

    rows = load_summary(args.summary, args.workload)
    grouped = group_by_stage_batch(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    n_runs = max(len(rs) for stage in grouped.values() for rs in stage.values())
    print(f"Loaded {len(rows)} rows for workload={args.workload!r} "
          f"(stages: {sorted(grouped)}, "
          f"batches: {sorted({b for s in grouped.values() for b in s})}, "
          f"max runs per cell: {n_runs})")
    print(f"Generating figures in: {args.out_dir}/")
    plot_overhead_stacked(grouped, args.out_dir)
    plot_crossover(grouped, args.out_dir)
    plot_e2e_decomp(grouped, args.out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
