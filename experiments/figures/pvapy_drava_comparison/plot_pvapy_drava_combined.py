#!/usr/bin/env python3
"""Combined PvaPy vs Drava PtychoNN throughput vs publisher rate.

Two panels in one figure, same style:
  (a) single-stage: best loss-free stage throughput vs publisher rate.
  (b) two-stage:    end-to-end pipeline throughput vs publisher rate (batch 128).

In both panels a runtime only has a point at a rate where it runs loss-free /
completes; the curve simply stops where it can no longer keep up (no annotations).

Inputs (curated CSVs in this directory):
  - pvapy_drava_ptychonn.csv          (single-stage; has a 'runtime' column)
  - pvapy_two_stage_summary.csv       (two-stage pvaPy, per-run)
  - drava_two_stage_summary.csv       (two-stage Drava, per-run)
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SINGLE_CSV = HERE / "pvapy_drava_ptychonn.csv"
PVAPY_TS_CSV = HERE / "pvapy_two_stage_summary.csv"
DRAVA_TS_CSV = HERE / "drava_two_stage_summary.csv"
FIGS_DIR = REPO_ROOT / "docs" / "figures" / "paper_figs"
NUM_FRAMES = 3600

COLORS = {"Drava": "#27667B", "PvaPy": "#C1662D"}
MARKERS = {"Drava": "o", "PvaPy": "s"}
# x-axis order shared by both panels; 0 == unpaced == "max".
ORDER = [1000, 2000, 2500, 3000, 0]
LABELS = {1000: "1k", 2000: "2k", 2500: "2.5k", 3000: "3k", 0: "max"}


def read_csv(path: Path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mean(v):
    return sum(v) / len(v) if v else 0.0


# ---- single stage: best loss-free stage throughput per (runtime, rate) --------
def single_stage_series(runtime):
    rows = read_csv(SINGLE_CSV)
    best = {}
    for r in rows:
        if r["runtime"] != runtime:
            continue
        if r["valid_stage_fps"] != "1" or int(r["missed_frames"]) != 0:
            continue
        rate = 0 if r["rate_hz"] == "max" else int(float(r["rate_hz"]))
        fps = float(r["stage_total_fps"])
        if rate not in best or fps > best[rate]:
            best[rate] = fps
    return best


# ---- two stage: end-to-end throughput over completed runs, fixed batch --------
def two_stage_series(rows, batch):
    by_rate = defaultdict(list)
    for r in rows:
        if int(r["batch"]) != batch:
            continue
        if float(r.get("stage2_side", 0) or 0) <= 0:
            continue
        e2e = float(r["pipeline_e2e_s"])
        if e2e > 0:
            by_rate[int(float(r["rate_hz"]))].append(NUM_FRAMES / e2e)
    return {rate: mean(v) for rate, v in by_rate.items()}


def fmt_k(x, _pos):
    return f"{x/1000:g}k" if x >= 1000 else f"{x:g}"


def plot_panel(ax, dr_map, pv_map, title, ylabel):
    xpos = {r: i for i, r in enumerate(ORDER)}

    def series(m):
        xs, ys = [], []
        for r in ORDER:
            if r in m and m[r] > 0:
                xs.append(xpos[r]); ys.append(m[r])
        return xs, ys

    dxs, dys = series(dr_map)
    pxs, pys = series(pv_map)
    ax.plot(dxs, dys, color=COLORS["Drava"], marker=MARKERS["Drava"],
            linewidth=2.4, markersize=6.5, label="Drava")
    ax.plot(pxs, pys, color=COLORS["PvaPy"], marker=MARKERS["PvaPy"],
            linewidth=2.4, markersize=6.5, label="PvaPy")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Publisher rate")
    ax.set_xticks(list(xpos.values()))
    ax.set_xticklabels([LABELS[r] for r in ORDER])
    ymax = max((dys + pys) or [1])
    ax.set_ylim(0, ymax * 1.18)
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=128, help="Two-stage batch size.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    dr_single = single_stage_series("Drava")
    pv_single = single_stage_series("PvaPy")
    dr_two = two_stage_series(read_csv(DRAVA_TS_CSV), args.batch)
    pv_two = two_stage_series(read_csv(PVAPY_TS_CSV), args.batch)

    plt.rcParams.update({
        "font.size": 11, "axes.labelsize": 11, "axes.titlesize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9.5,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)
    plot_panel(axa, dr_single, pv_single,
               "(a) single-stage inference", "Stage throughput (frames/s)")
    plot_panel(axb, dr_two, pv_two,
               f"(b) two-stage pipeline", "End-to-end throughput (frames/s)")
    axa.legend(loc="upper left", frameon=False)

    out_base = Path(args.out).resolve() if args.out else FIGS_DIR / "pvapy_drava_combined"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
