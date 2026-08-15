#!/usr/bin/env python3
r"""PvaPy HPC distributor scaling: throughput and latency vs consumer count.

The point of this figure: on PvaPy's supported multi-consumer path (the HPC data
distributor), adding stage-2 consumers does NOT improve performance. The stream
is already delivered loss-free at N=1 because GPU stage-1 throttles it, so
splitting the cheap CPU stitch across more processes only adds distributor and
IPC overhead. End-to-end throughput drops (about 455 fps at N=1 to 82 fps at N=8)
and latency rises (about 8s to 44s), and every PvaPy point is worse than Drava's
single-process two-stage pipeline (dashed reference, ~1200 fps / ~3s).

Both metrics are measured identically to Drava's benchmark_two_stages.py: first
frame sent -> last stage-2 object received. Bars are mean over rate x run.

Inputs (curated CSVs in this directory):
  - pvapy_hpc_distributor_sweep.csv   (this sweep, has pipeline_e2e_s/pipeline_fps)
  - drava_two_stage_summary.csv       (Drava two-stage e2e, for the reference)
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

COLOR_BAR = "#C1662D"   # PvaPy orange (matches combined figure)
COLOR_DRAVA = "#27667B"  # Drava teal


def read_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def drava_reference():
    """Mean Drava two-stage e2e latency and throughput over paced rates (batch 128)."""
    lat = []
    for r in read_rows(DRAVA_TS_CSV):
        try:
            if int(r["batch"]) != 128:
                continue
            if int(float(r["rate_hz"])) == 0:  # exclude unpaced "max"
                continue
            e2e = float(r["pipeline_e2e_s"])
            if e2e > 0:
                lat.append(e2e)
        except (KeyError, ValueError):
            continue
    if not lat:
        return None, None
    lat_ref = mean(lat)
    fps_ref = mean(NUM_FRAMES / v for v in lat)
    return fps_ref, lat_ref


def plot_panel(ax, ns, mean_vals, std_vals, drava_val, ylabel, ref_label_loc):
    x = list(range(len(ns)))
    ax.bar(x, mean_vals, yerr=std_vals, width=0.6, color=COLOR_BAR,
           error_kw={"elinewidth": 1.0, "capsize": 2, "capthick": 1.0,
                     "ecolor": "#3a3a3a"},
           label="PvaPy consumers")
    if drava_val is not None:
        ax.axhline(drava_val, color=COLOR_DRAVA, linestyle="--", linewidth=2.2,
                   label="Drava (1 process)")
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in ns])
    ax.set_xlabel("PvaPy stage-2 consumers $N$")
    ax.set_ylabel(ylabel)
    ymax = max(mean_vals + ([drava_val] if drava_val else []))
    ax.set_ylim(0, ymax * 1.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)
    ax.legend(loc=ref_label_loc, frameon=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = read_rows(SWEEP_CSV)
    lat = defaultdict(list)
    fps = defaultdict(list)
    for r in rows:
        if r["pipeline_e2e_s"]:
            lat[int(r["n_consumers"])].append(float(r["pipeline_e2e_s"]))
        if r["pipeline_fps"]:
            fps[int(r["n_consumers"])].append(float(r["pipeline_fps"]))

    ns = sorted(lat)
    lat_mean = [mean(lat[n]) for n in ns]
    lat_std = [pstdev(lat[n]) if len(lat[n]) > 1 else 0.0 for n in ns]
    fps_mean = [mean(fps[n]) for n in ns]
    fps_std = [pstdev(fps[n]) if len(fps[n]) > 1 else 0.0 for n in ns]
    fps_ref, lat_ref = drava_reference()

    plt.rcParams.update({
        "font.size": 11, "axes.labelsize": 11, "axes.titlesize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9.0,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)
    plot_panel(axa, ns, fps_mean, fps_std, fps_ref,
               "End-to-end throughput (frames/s)", "center right")
    plot_panel(axb, ns, lat_mean, lat_std, lat_ref,
               "End-to-end latency (s)", "upper left")
    axa.set_title("(a) throughput")
    axb.set_title("(b) latency")

    out_base = Path(args.out).resolve() if args.out else FIGS_DIR / "pvapy_distributor_scaling"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
