#!/usr/bin/env python3
"""Two-stage PtychoNN comparison: end-to-end throughput vs publisher rate.

Mirrors the single-stage figure (throughput vs publisher rate) but for the full
two-stage pipeline (GPU inference -> CPU stitching). We fix the inference batch
size and sweep the publisher rate. End-to-end pipeline throughput is
frames / end_to_end_latency over runs that completed a full stitch. Where a
runtime fails to complete the pipeline (drops a stage-boundary message), it has
no loss-free point at that rate, so the curve stops -- exactly like the
single-stage loss curve.

Inputs (curated CSVs in this directory), per-run rows with columns:
  rate_hz,batch,run,stage1_total_fps,stage2_total_fps,stage2_side,pipeline_e2e_s
  - pvapy_two_stage_summary.csv
  - drava_two_stage_summary.csv
A run "completed" iff stage2_side > 0.
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
PVAPY_CSV = HERE / "pvapy_two_stage_summary.csv"
DRAVA_CSV = HERE / "drava_two_stage_summary.csv"
FIGS_DIR = REPO_ROOT / "figs" / "paper_figs"
NUM_FRAMES = 3600

COLORS = {"Drava": "#27667B", "PvaPy": "#C1662D"}
MARKERS = {"Drava": "o", "PvaPy": "s"}


def read_csv(path: Path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mean(v):
    return sum(v) / len(v) if v else 0.0


def e2e_throughput_by_rate(rows, batch):
    """Return {rate_hz: mean end-to-end throughput (fps)} over completed runs
    at the given batch. rate_hz=0 is treated as 'max' (unpaced)."""
    by_rate = defaultdict(list)
    for r in rows:
        if int(r["batch"]) != batch:
            continue
        if float(r.get("stage2_side", 0) or 0) <= 0:
            continue  # incomplete run: no loss-free point
        e2e = float(r["pipeline_e2e_s"])
        if e2e > 0:
            by_rate[int(float(r["rate_hz"]))].append(NUM_FRAMES / e2e)
    return {rate: mean(v) for rate, v in by_rate.items()}


def completion_by_rate(rows, batch):
    by_rate = defaultdict(list)
    for r in rows:
        if int(r["batch"]) != batch:
            continue
        by_rate[int(float(r["rate_hz"]))].append(
            1 if float(r.get("stage2_side", 0) or 0) > 0 else 0)
    return {rate: (sum(v), len(v)) for rate, v in by_rate.items()}


def fmt_k(x, _pos):
    return f"{x/1000:g}k" if x >= 1000 else f"{x:g}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=128,
                    help="Fixed inference batch size for the rate sweep.")
    ap.add_argument("--rates", default="1000,2000,2500,3000,0",
                    help="Rate order for the x-axis (0 = unpaced/max).")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    order = [int(x) for x in args.rates.split(",") if x.strip()]
    labels = {r: (f"{r//1000}k" if r >= 1000 else ("max" if r == 0 else str(r)))
              for r in order}
    labels_special = {2500: "2.5k"}
    for k, v in labels_special.items():
        if k in labels:
            labels[k] = v

    pv = read_csv(PVAPY_CSV)
    dr = read_csv(DRAVA_CSV)

    dr_tput = e2e_throughput_by_rate(dr, args.batch)
    pv_tput = e2e_throughput_by_rate(pv, args.batch)
    pv_comp = completion_by_rate(pv, args.batch)

    plt.rcParams.update({
        "font.size": 11, "axes.labelsize": 11, "axes.titlesize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(5.0, 3.0), constrained_layout=True)
    xpos = {r: i for i, r in enumerate(order)}

    def series(tput):
        xs, ys = [], []
        for r in order:
            if r in tput and tput[r] > 0:
                xs.append(xpos[r]); ys.append(tput[r])
        return xs, ys

    dxs, dys = series(dr_tput)
    pxs, pys = series(pv_tput)
    ax.plot(dxs, dys, color=COLORS["Drava"], marker=MARKERS["Drava"],
            linewidth=2.4, markersize=6.5, label="Drava")
    ax.plot(pxs, pys, color=COLORS["PvaPy"], marker=MARKERS["PvaPy"],
            linewidth=2.4, markersize=6.5, label="PvaPy")

    # Mark rates where PvaPy could not complete the pipeline (no loss-free point).
    ymax = max(dys + pys) if (dys + pys) else 1.0
    for r in order:
        done, total = pv_comp.get(r, (0, 0))
        if total and done == 0:
            ax.annotate("PvaPy\nfails", xy=(xpos[r], 0.06 * ymax),
                        ha="center", va="bottom", fontsize=8,
                        color=COLORS["PvaPy"])

    ax.set_title(f"Two-stage PtychoNN end-to-end throughput (batch {args.batch})")
    ax.set_ylabel("End-to-end throughput (frames/s)")
    ax.set_xlabel("Publisher rate")
    ax.set_xticks(list(xpos.values()))
    ax.set_xticklabels([labels[r] for r in order])
    ax.set_ylim(0, ymax * 1.25)
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", frameon=False)

    out_base = Path(args.out).resolve() if args.out else FIGS_DIR / "pvapy_drava_two_stage"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
