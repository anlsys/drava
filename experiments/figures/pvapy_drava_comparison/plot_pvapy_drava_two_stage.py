#!/usr/bin/env python3
"""Two-stage PtychoNN comparison: Drava vs pvaPy.

Shows that Drava completes the full two-stage pipeline loss-free while the pvaPy
single-record PvaServer path drops stage-1 predictions at the stage boundary and
usually cannot finalize the stitch.

Inputs (curated CSVs in this directory):
  - pvapy_two_stage_summary.csv : per-run pvaPy rows with a `completed` flag
  - drava_two_stage_summary.csv : per-run Drava rows (from benchmark_two_stages.py)

Panel (a): pipeline completion rate (% of runs that finalized the stitch) per batch.
Panel (b): end-to-end latency for COMPLETED runs (mean +/- std); pvaPy shown only
           where it completed.

Usage:
  python plot_pvapy_drava_two_stage.py            # rate_hz=1000 by default
  python plot_pvapy_drava_two_stage.py --rate-hz 1000
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

GREEN = "#6A8F7A"   # Drava
ORANGE = "#B5651D"  # pvaPy


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mean(v):
    return float(np.mean(v)) if v else 0.0


def std(v):
    return float(np.std(v, ddof=1)) if len(v) > 1 else 0.0


def load_pvapy(rate_hz: int):
    rows = [r for r in read_csv(PVAPY_CSV) if int(float(r["rate_hz"])) == rate_hz]
    by_batch = defaultdict(list)
    for r in rows:
        by_batch[int(r["batch"])].append(r)
    comp_rate, e2e_mean, e2e_std = {}, {}, {}
    for b, rs in by_batch.items():
        flags = [int(r["completed"]) for r in rs]
        comp_rate[b] = 100.0 * sum(flags) / len(flags)
        e2e = [float(r["pipeline_e2e_s"]) for r in rs if int(r["completed"]) == 1]
        e2e_mean[b] = mean(e2e)
        e2e_std[b] = std(e2e)
    return comp_rate, e2e_mean, e2e_std


def load_drava(rate_hz: int):
    rows = [r for r in read_csv(DRAVA_CSV) if int(float(r.get("rate_hz", rate_hz))) == rate_hz] \
        or read_csv(DRAVA_CSV)  # tolerate summaries without a rate column
    by_batch = defaultdict(list)
    for r in rows:
        by_batch[int(r["batch"])].append(r)
    comp_rate, e2e_mean, e2e_std = {}, {}, {}
    for b, rs in by_batch.items():
        # A Drava run "completed" if it produced a stitched side > 0.
        flags = [1 if float(r.get("stage2_side", 0) or 0) > 0 else 0 for r in rs]
        comp_rate[b] = 100.0 * sum(flags) / len(flags) if flags else 0.0
        e2e = [float(r["pipeline_e2e_s"]) for r in rs
               if r.get("pipeline_e2e_s") not in (None, "", "None")]
        e2e_mean[b] = mean(e2e)
        e2e_std[b] = std(e2e)
    return comp_rate, e2e_mean, e2e_std


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate-hz", type=int, default=1000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pv_comp, pv_e2e_m, pv_e2e_s = load_pvapy(args.rate_hz)
    dr_comp, dr_e2e_m, dr_e2e_s = load_drava(args.rate_hz)

    batches = sorted(set(pv_comp) | set(dr_comp))
    if not batches:
        raise SystemExit("No data. Ensure pvapy_two_stage_summary.csv and "
                         "drava_two_stage_summary.csv exist for the chosen rate.")

    plt.rcParams.update({
        "font.size": 12, "axes.labelsize": 13, "xtick.labelsize": 11,
        "ytick.labelsize": 11, "legend.fontsize": 11, "axes.titlesize": 13,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.7), constrained_layout=True)
    x = np.arange(len(batches))
    w = 0.38

    # (a) completion rate
    ax1.bar(x - w / 2, [dr_comp.get(b, 0) for b in batches], w, color=GREEN,
            edgecolor="#2E4A3A", label="Drava")
    ax1.bar(x + w / 2, [pv_comp.get(b, 0) for b in batches], w, color=ORANGE,
            edgecolor="#6E3D10", label="PvaPy")
    ax1.set_ylabel("Pipeline completion (%)")
    ax1.set_xlabel("Inference batch size")
    ax1.set_xticks(x); ax1.set_xticklabels([str(b) for b in batches])
    ax1.set_ylim(0, 108)
    ax1.grid(True, axis="y", color="#E0E0E0", linewidth=0.7); ax1.set_axisbelow(True)
    for sp in ("top", "right"): ax1.spines[sp].set_visible(False)
    ax1.set_title("(a) completion rate")
    ax1.legend(frameon=False, loc="lower center", ncol=2)

    # (b) end-to-end latency for completed runs
    dr_m = [dr_e2e_m.get(b, 0) for b in batches]
    dr_s = [dr_e2e_s.get(b, 0) for b in batches]
    pv_m = [pv_e2e_m.get(b, 0) for b in batches]
    pv_s = [pv_e2e_s.get(b, 0) for b in batches]
    ax2.bar(x - w / 2, dr_m, w, yerr=dr_s, capsize=3, color=GREEN,
            edgecolor="#2E4A3A", label="Drava",
            error_kw={"elinewidth": 0.9, "capthick": 0.9})
    # pvaPy bars only where it completed at least once (mean > 0).
    pv_m_plot = [m if m > 0 else np.nan for m in pv_m]
    ax2.bar(x + w / 2, pv_m_plot, w, yerr=pv_s, capsize=3, color=ORANGE,
            edgecolor="#6E3D10", label="PvaPy (completed only)",
            error_kw={"elinewidth": 0.9, "capthick": 0.9})
    ax2.set_ylabel("End-to-end latency (s)")
    ax2.set_xlabel("Inference batch size")
    ax2.set_xticks(x); ax2.set_xticklabels([str(b) for b in batches])
    ax2.grid(True, axis="y", color="#E0E0E0", linewidth=0.7); ax2.set_axisbelow(True)
    for sp in ("top", "right"): ax2.spines[sp].set_visible(False)
    ax2.set_title("(b) end-to-end latency")
    ax2.legend(frameon=False, loc="upper right")

    out_base = Path(args.out).resolve() if args.out else OUT_BASE
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
