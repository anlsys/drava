#!/usr/bin/env python3
"""Two-stage PtychoNN comparison: Drava vs pvaPy.

The reconstruction needs every stage-1 prediction to stitch the scan, so a single
dropped inter-stage message fails the whole run. This plot shows pipeline
completion rate (fraction of runs that produced a full stitched reconstruction)
as a function of inference batch size, for pvaPy at 1 and 2 kHz and Drava. The
pvaPy single-record path degrades with batch size and rate, while Drava's durable
transport completes every run.

Inputs (curated CSVs in this directory):
  - pvapy_two_stage_summary.csv : per-run pvaPy rows (stage2_side>0 => completed)
  - drava_two_stage_summary.csv : per-run Drava rows

A run "completed" iff stage2_side > 0 (a full stitch was produced).
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
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
PVAPY_CSV = HERE / "pvapy_two_stage_summary.csv"
DRAVA_CSV = HERE / "drava_two_stage_summary.csv"
OUT_BASE = ROOT / "figs" / "paper_figs" / "pvapy_drava_two_stage"

GREEN = "#6A8F7A"    # Drava
ORANGE = "#B5651D"   # pvaPy 1 kHz
ORANGE2 = "#E0A458"  # pvaPy 2 kHz (lighter)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def completion_by_batch(rows, rate_hz):
    """Return {batch: completion_percent} for the given rate."""
    by_batch = defaultdict(list)
    for r in rows:
        if int(float(r.get("rate_hz", rate_hz))) != rate_hz:
            continue
        by_batch[int(r["batch"])].append(r)
    out = {}
    for b, rs in by_batch.items():
        done = sum(1 for r in rs if float(r.get("stage2_side", 0) or 0) > 0)
        out[b] = 100.0 * done / len(rs) if rs else 0.0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rates", default="1000,2000", help="Comma-separated pvaPy rates to show.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rates = [int(x) for x in args.rates.split(",") if x.strip()]
    pv_rows = read_csv(PVAPY_CSV)
    dr_rows = read_csv(DRAVA_CSV)

    pv_comp = {r: completion_by_batch(pv_rows, r) for r in rates}
    # Drava completes every run at all rates; aggregate over all Drava rows.
    dr_comp_all = defaultdict(list)
    for r in dr_rows:
        dr_comp_all[int(r["batch"])].append(r)
    dr_comp = {
        b: 100.0 * sum(1 for x in rs if float(x.get("stage2_side", 0) or 0) > 0) / len(rs)
        for b, rs in dr_comp_all.items()
    }

    batches = sorted(set(dr_comp) | {b for r in rates for b in pv_comp[r]})
    if not batches:
        raise SystemExit("No data found in the two-stage summary CSVs.")

    plt.rcParams.update({
        "font.size": 12, "axes.labelsize": 13, "xtick.labelsize": 11,
        "ytick.labelsize": 11, "legend.fontsize": 10.5, "axes.titlesize": 13,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(4.4, 3.0), constrained_layout=True)
    x = np.arange(len(batches), dtype=float)

    series = [("Drava", dr_comp, GREEN, "#2E4A3A")]
    for i, r in enumerate(rates):
        label = f"PvaPy {r//1000}\u2009kHz"
        color = ORANGE if r == rates[0] else ORANGE2
        edge = "#6E3D10"
        series.append((label, pv_comp[r], color, edge))

    n = len(series)
    w = 0.8 / n
    for i, (label, comp, fc, ec) in enumerate(series):
        offset = (i - (n - 1) / 2.0) * w
        vals = [comp.get(b, 0.0) for b in batches]
        bars = ax.bar(x + offset, vals, w * 0.95, color=fc, edgecolor=ec,
                      linewidth=0.8, label=label, zorder=2)
        # Annotate zero-completion bars with a small "0".
        for xi, v in zip(x + offset, vals):
            if v == 0:
                ax.text(xi, 2, "0", ha="center", va="bottom", fontsize=9,
                        color=ec)

    ax.set_ylabel("Pipeline completion (%)")
    ax.set_xlabel("Inference batch size")
    ax.set_xticks(x); ax.set_xticklabels([str(b) for b in batches])
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.grid(True, axis="y", color="#E0E0E0", linewidth=0.7); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, loc="lower left", ncol=1)

    out_base = Path(args.out).resolve() if args.out else OUT_BASE
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
