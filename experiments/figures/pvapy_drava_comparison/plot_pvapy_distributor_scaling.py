#!/usr/bin/env python3
r"""PvaPy HPC distributor scaling: throughput, latency, and completion vs N.

On PvaPy's supported multi-consumer path (the HPC data distributor), the
distributor delivers every frame loss-free at every N (no distributor-caused
loss in the sweep), so adding consumers does NOT improve delivery. It only hurts
performance:
  (a) end-to-end throughput drops (about 455 fps at N=1 to 82 fps at N=8),
  (b) end-to-end latency rises (about 8s to 44s),
because GPU stage-1 sets the pace and extra consumers add coordination overhead.
Every configuration is worse than Drava (dashed reference, ~1200 fps / ~3s,
always loss-free), which needs no per-stage consumer or queue tuning. Separately,
a single consumer is crash-prone at teardown, so N>=2 is safer, but that is
stated in prose, not this figure.

Throughput/latency measured identically to Drava's benchmark_two_stages.py:
first frame sent -> last stage-2 object received. Bars are mean over rate x run.

Inputs (curated CSVs in this directory):
  - pvapy_hpc_distributor_sweep.csv
  - drava_two_stage_summary.csv
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
DRAVA_TS_CSV = HERE / "drava_two_stage_summary.csv"
FIGS_DIR = REPO_ROOT / "figs" / "paper_figs"
NUM_FRAMES = 3600

# Shared comparison palette (Drava vs PvaPy) used across all comparison figures.
COLOR_PVAPY = "#C1662D"   # PvaPy orange
COLOR_DRAVA = "#27667B"   # Drava teal


def read_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def drava_reference():
    """Mean Drava two-stage e2e latency and throughput over paced rates (batch 128)."""
    lat = []
    for r in read_rows(DRAVA_TS_CSV):
        try:
            if int(r["batch"]) != 128 or int(float(r["rate_hz"])) == 0:
                continue
            e2e = float(r["pipeline_e2e_s"])
            if e2e > 0:
                lat.append(e2e)
        except (KeyError, ValueError):
            continue
    if not lat:
        return None, None
    return mean(NUM_FRAMES / v for v in lat), mean(lat)


def bar_panel(ax, ns, mean_vals, std_vals, drava_val, ylabel, title, legend_loc):
    x = list(range(len(ns)))
    ax.bar(x, mean_vals, yerr=std_vals, width=0.62, color=COLOR_PVAPY,
           error_kw={"elinewidth": 1.0, "capsize": 2, "capthick": 1.0,
                     "ecolor": "#3a3a3a"},
           label="PvaPy")
    if drava_val is not None:
        ax.axhline(drava_val, color=COLOR_DRAVA, linestyle="--", linewidth=2.2,
                   label="Drava")
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in ns])
    ax.set_xlabel("Consumers $N$")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ymax = max(mean_vals + ([drava_val] if drava_val else []))
    ax.set_ylim(0, ymax * 1.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)
    if legend_loc:
        ax.legend(loc=legend_loc, frameon=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = read_rows(SWEEP_CSV)
    lat = defaultdict(list)
    fps = defaultdict(list)
    runs = defaultdict(int)
    complete = defaultdict(int)
    for r in rows:
        n = int(r["n_consumers"])
        runs[n] += 1
        if r["complete"] == "1":
            complete[n] += 1
        if r["pipeline_e2e_s"]:
            lat[n].append(float(r["pipeline_e2e_s"]))
        if r["pipeline_fps"]:
            fps[n].append(float(r["pipeline_fps"]))

    ns = sorted(runs)
    fps_mean = [mean(fps[n]) if fps[n] else 0.0 for n in ns]
    fps_std = [pstdev(fps[n]) if len(fps[n]) > 1 else 0.0 for n in ns]
    lat_mean = [mean(lat[n]) if lat[n] else 0.0 for n in ns]
    lat_std = [pstdev(lat[n]) if len(lat[n]) > 1 else 0.0 for n in ns]
    fps_ref, lat_ref = drava_reference()

    plt.rcParams.update({
        "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 8.5,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.2, 3.0),
                                   constrained_layout=True)
    bar_panel(axa, ns, fps_mean, fps_std, fps_ref,
              "End-to-end throughput (frames/s)", "(a) throughput", "center right")
    bar_panel(axb, ns, lat_mean, lat_std, lat_ref,
              "End-to-end latency (s)", "(b) latency", "upper left")

    out_base = Path(args.out).resolve() if args.out else FIGS_DIR / "pvapy_distributor_scaling"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
