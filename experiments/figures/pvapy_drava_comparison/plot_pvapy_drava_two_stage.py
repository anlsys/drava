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


def _agg(rows, batches_filter=None):
    """Return per-batch completion rate (%) and, for completed runs only
    (stitched side > 0), mean/std of end-to-end latency and stage-2 fps."""
    by_batch = defaultdict(list)
    for r in rows:
        by_batch[int(r["batch"])].append(r)
    comp, e2e_m, e2e_s, fps_m, fps_s = {}, {}, {}, {}, {}
    for b, rs in by_batch.items():
        done = [r for r in rs if float(r.get("stage2_side", 0) or 0) > 0]
        comp[b] = 100.0 * len(done) / len(rs) if rs else 0.0
        e2e = [float(r["pipeline_e2e_s"]) for r in done
               if r.get("pipeline_e2e_s") not in (None, "", "None")]
        fps = [float(r["stage2_total_fps"]) for r in done
               if r.get("stage2_total_fps") not in (None, "", "None")]
        e2e_m[b], e2e_s[b] = mean(e2e), std(e2e)
        fps_m[b], fps_s[b] = mean(fps), std(fps)
    return comp, e2e_m, e2e_s, fps_m, fps_s


def load_pvapy(rate_hz: int):
    rows = [r for r in read_csv(PVAPY_CSV) if int(float(r["rate_hz"])) == rate_hz]
    return _agg(rows)


def load_drava(rate_hz: int):
    all_rows = read_csv(DRAVA_CSV)
    rows = [r for r in all_rows if int(float(r.get("rate_hz", rate_hz))) == rate_hz] or all_rows
    return _agg(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate-hz", type=int, default=1000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pv_comp, pv_e2e_m, pv_e2e_s, pv_fps_m, pv_fps_s = load_pvapy(args.rate_hz)
    dr_comp, dr_e2e_m, dr_e2e_s, dr_fps_m, dr_fps_s = load_drava(args.rate_hz)

    batches = sorted(set(pv_comp) | set(dr_comp))
    if not batches:
        raise SystemExit("No data. Ensure pvapy_two_stage_summary.csv and "
                         "drava_two_stage_summary.csv exist for the chosen rate.")

    plt.rcParams.update({
        "font.size": 12, "axes.labelsize": 12.5, "xtick.labelsize": 11,
        "ytick.labelsize": 11, "legend.fontsize": 11, "axes.titlesize": 12.5,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    fig, (ax0, ax1, ax2) = plt.subplots(1, 3, figsize=(7.2, 2.5), constrained_layout=True)
    x = np.arange(len(batches))
    w = 0.38
    err_kw = {"elinewidth": 0.9, "capthick": 0.9}

    def paired_bars(ax, dmap, dstd, pmap, pstd):
        ax.bar(x - w / 2, [dmap.get(b, 0) for b in batches], w,
               yerr=None if dstd is None else [dstd.get(b, 0) for b in batches],
               capsize=3, color=GREEN, edgecolor="#2E4A3A", label="Drava", error_kw=err_kw)
        ax.bar(x + w / 2, [pmap.get(b, 0) for b in batches], w,
               yerr=None if pstd is None else [pstd.get(b, 0) for b in batches],
               capsize=3, color=ORANGE, edgecolor="#6E3D10", label="PvaPy", error_kw=err_kw)
        ax.set_xlabel("Batch size")
        ax.set_xticks(x); ax.set_xticklabels([str(b) for b in batches])
        ax.grid(True, axis="y", color="#E0E0E0", linewidth=0.7); ax.set_axisbelow(True)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)

    # (a) completion rate
    paired_bars(ax0, dr_comp, None, pv_comp, None)
    ax0.set_ylabel("Completion (%)")
    ax0.set_ylim(0, 108)
    ax0.set_title("(a) completion")
    ax0.legend(frameon=False, loc="lower center", ncol=1)

    # (b) end-to-end latency (completed runs; lower is better)
    paired_bars(ax1, dr_e2e_m, dr_e2e_s, pv_e2e_m, pv_e2e_s)
    ax1.set_ylabel("E2E latency (s)")
    ax1.set_title("(b) latency")

    # (c) stage-2 throughput (completed runs; higher is better)
    paired_bars(ax2, dr_fps_m, dr_fps_s, pv_fps_m, pv_fps_s)
    ax2.set_ylabel("Stage-2 fps")
    ax2.set_title("(c) throughput")

    out_base = Path(args.out).resolve() if args.out else OUT_BASE
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
        print(out_base.with_suffix(f".{ext}"))


if __name__ == "__main__":
    main()
