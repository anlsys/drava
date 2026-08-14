#!/usr/bin/env python3
r"""PvaPy HPC distributor scaling: end-to-end latency vs consumer count.

The point of this figure: on PvaPy's supported multi-consumer path (the HPC data
distributor), adding stage-2 consumers does NOT improve performance. The stream
is already delivered loss-free at N=1 because GPU stage-1 throttles it, so
splitting the cheap CPU stitch across more processes only adds distributor and
IPC overhead. End-to-end latency therefore rises monotonically with N (about 8s
at N=1 up to 44s at N=8), and every PvaPy point is slower than Drava's
single-process two-stage pipeline (~3s, dashed reference).

Latency is measured identically to Drava's benchmark_two_stages.py: first frame
sent -> last stage-2 object received. Bars are mean over rate x run.

Inputs (curated CSVs in this directory):
  - pvapy_hpc_distributor_sweep.csv   (this sweep, has pipeline_e2e_s)
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


def drava_reference_latency():
    """Mean Drava two-stage end-to-end latency over paced rates (batch 128)."""
    vals = []
    for r in read_rows(DRAVA_TS_CSV):
        try:
            if int(r["batch"]) != 128:
                continue
            rate = int(float(r["rate_hz"]))
            if rate == 0:  # exclude unpaced "max" so the ref matches paced sweep
                continue
            e2e = float(r["pipeline_e2e_s"])
            if e2e > 0:
                vals.append(e2e)
        except (KeyError, ValueError):
            continue
    return mean(vals) if vals else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = read_rows(SWEEP_CSV)
    lat = defaultdict(list)  # N -> [pipeline_e2e_s] over complete runs
    for r in rows:
        if r["pipeline_e2e_s"]:
            lat[int(r["n_consumers"])].append(float(r["pipeline_e2e_s"]))

    ns = sorted(lat)
    lat_mean = [mean(lat[n]) for n in ns]
    lat_std = [pstdev(lat[n]) if len(lat[n]) > 1 else 0.0 for n in ns]
    drava_ref = drava_reference_latency()

    plt.rcParams.update({
        "font.size": 11, "axes.labelsize": 11, "axes.titlesize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9.5,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(3.6, 3.0), constrained_layout=True)
    x = list(range(len(ns)))
    ax.bar(x, lat_mean, yerr=lat_std, width=0.6, color=COLOR_BAR,
           error_kw={"elinewidth": 1.0, "capsize": 2, "capthick": 1.0,
                     "ecolor": "#3a3a3a"},
           label="PvaPy consumers")

    if drava_ref is not None:
        ax.axhline(drava_ref, color=COLOR_DRAVA, linestyle="--", linewidth=2.2,
                   label="Drava (1 process)")

    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in ns])
    ax.set_xlabel("Number of PvaPy stage-2 consumers $N$")
    ax.set_ylabel("End-to-end latency (s)")
    ymax = max(lat_mean + ([drava_ref] if drava_ref else []))
    ax.set_ylim(0, ymax * 1.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)
    ax.legend(loc="upper left", frameon=False)

    out_base = Path(args.out).resolve() if args.out else FIGS_DIR / "pvapy_distributor_scaling"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
