#!/usr/bin/env python3
r"""PvaPy HPC distributor: stage-2 wall time and completeness vs consumer count.

The point of this figure: on PvaPy's supported multi-consumer path (the HPC data
distributor), adding stage-2 consumers does NOT improve completeness---the run is
already loss-free at N=1 because the GPU stage-1 throttles the stream---while it
monotonically increases end-to-end (stage-2) wall time. So over-provisioning
consumers only costs latency, and the operator must guess the right N. \drava{}
needs a single process with no such tuning.

Left axis:  mean stage-2 wall time vs N (bars, error bars over rate x run).
Right axis: fraction of runs that completed loss-free vs N (flat line ~1).

Input: pvapy_hpc_distributor_sweep.csv in this directory.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SWEEP_CSV = HERE / "pvapy_hpc_distributor_sweep.csv"
FIGS_DIR = REPO_ROOT / "figs" / "paper_figs"

COLOR_BAR = "#C1662D"   # PvaPy orange (matches combined figure)
COLOR_LINE = "#27667B"  # Drava teal, reused for the completeness overlay


def read_rows():
    with open(SWEEP_CSV, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = read_rows()
    # A run is "crashed" if it produced no consumer output (union==0); exclude
    # those from wall-time stats but count them against completeness.
    walls = defaultdict(list)       # N -> [stage2_wall_s] for runs that produced output
    complete_flags = defaultdict(list)  # N -> [0/1] over ALL runs
    for r in rows:
        n = int(r["n_consumers"])
        crashed = (r["union_frames"] == "0")
        complete_flags[n].append(int(r["complete"]))
        if not crashed:
            walls[n].append(float(r["stage2_wall_s"]))

    ns = sorted(walls)
    wall_mean = [mean(walls[n]) for n in ns]
    wall_std = [pstdev(walls[n]) if len(walls[n]) > 1 else 0.0 for n in ns]
    complete_frac = [mean(complete_flags[n]) for n in ns]

    plt.rcParams.update({
        "font.size": 11, "axes.labelsize": 11, "axes.titlesize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9.5,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(3.6, 3.0), constrained_layout=True)
    x = list(range(len(ns)))
    ax.bar(x, wall_mean, yerr=wall_std, width=0.6, color=COLOR_BAR,
           capsize=4, label="Stage-2 wall time")
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in ns])
    ax.set_xlabel("Number of stage-2 consumers $N$")
    ax.set_ylabel("Stage-2 wall time (s)")
    ax.set_ylim(0, max(wall_mean) * 1.25)
    ax.spines["top"].set_visible(False)
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)

    ax2 = ax.twinx()
    ax2.plot(x, [c * 100 for c in complete_frac], color=COLOR_LINE,
             marker="o", linewidth=2.2, markersize=6, label="Loss-free runs")
    ax2.set_ylabel("Loss-free runs (%)", color=COLOR_LINE)
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="y", labelcolor=COLOR_LINE)
    ax2.spines["top"].set_visible(False)

    # combined legend
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)

    out_base = Path(args.out).resolve() if args.out else FIGS_DIR / "pvapy_distributor_scaling"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
