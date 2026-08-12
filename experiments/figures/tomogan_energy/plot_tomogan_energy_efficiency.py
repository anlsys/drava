#!/usr/bin/env python3
from __future__ import annotations

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


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = HERE / "tomogan_energy_efficiency_data.csv"
OUT_DIR = ROOT / "figures"
OUT_BASE = OUT_DIR / "tomogan_energy_efficiency"


def read_rows() -> list[dict[str, str]]:
    with open(DATA, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mean(values: list[float]) -> float:
    return float(np.mean(values))


def stdev(values: list[float]) -> float:
    return float(np.std(values, ddof=1)) if len(values) > 1 else 0.0


def _has_col(grouped, batches, col: str) -> bool:
    return all(
        col in r and r[col] not in (None, "", "None")
        for b in batches for r in grouped[b]
    )


def eff_stats(grouped, batches, col):
    """Mean/std of energy efficiency (frames/J) = 1 / (J/frame)."""
    m = [mean([1.0 / float(r[col]) for r in grouped[b]]) for b in batches]
    s = [stdev([1.0 / float(r[col]) for r in grouped[b]]) for b in batches]
    return np.asarray(m), np.asarray(s)


def main() -> None:
    rows = read_rows()
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["batch"])].append(row)

    batches = sorted(grouped)
    has_cpu = _has_col(grouped, batches, "cpu_energy_j_per_frame")
    has_total = _has_col(grouped, batches, "total_energy_j_per_frame")

    gpu_m, gpu_s = eff_stats(grouped, batches, "gpu_energy_j_per_frame")
    if has_cpu:
        cpu_m, cpu_s = eff_stats(grouped, batches, "cpu_energy_j_per_frame")
    if has_total:
        tot_m, tot_s = eff_stats(grouped, batches, "total_energy_j_per_frame")

    fps_mean = np.asarray([mean([float(r["stage_fps"]) for r in grouped[b]]) for b in batches])
    fps_std = np.asarray([stdev([float(r["stage_fps"]) for r in grouped[b]]) for b in batches])

    plt.rcParams.update({
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(3.6, 2.55), constrained_layout=True)
    x = np.arange(len(batches))

    # Grouped bars: GPU, CPU, Total energy efficiency (frames/J), higher is better.
    series = [("GPU", gpu_m, gpu_s, "#6A8F7A", "#2E4A3A")]
    if has_cpu:
        series.append(("CPU", cpu_m, cpu_s, "#B5651D", "#6E3D10"))
    if has_total:
        series.append(("Total", tot_m, tot_s, "#3B6FB0", "#22436B"))

    n = len(series)
    width = 0.8 / n
    err_kw = {"elinewidth": 0.9, "capthick": 0.9, "ecolor": "#333333"}
    ymax = 0.0
    for i, (label, m, s, fc, ec) in enumerate(series):
        offset = (i - (n - 1) / 2.0) * width
        ax.bar(x + offset, m, yerr=s, width=width * 0.95, capsize=2.5,
               color=fc, edgecolor=ec, linewidth=0.7, label=label,
               error_kw=err_kw, zorder=2)
        ymax = max(ymax, float(np.max(m + s)))

    ax.set_xticks(x)
    ax.set_xticklabels([str(b) for b in batches])
    ax.set_xlabel("Callback-inference batch size")
    ax.set_ylabel("Energy efficiency (frames/J)")
    ax.set_ylim(0, ymax * 1.20)
    ax.grid(True, axis="y", color="#D6D6D6", linewidth=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # Throughput line on secondary axis.
    ax2 = ax.twinx()
    ax2.fill_between(x, fps_mean - fps_std, fps_mean + fps_std,
                     color="#111111", alpha=0.10, linewidth=0, zorder=1)
    ax2.errorbar(x, fps_mean, yerr=fps_std, color="#111111", marker="o",
                 markersize=4, linewidth=1.5, capsize=3, elinewidth=0.9,
                 capthick=0.9, zorder=3, label="throughput")
    ax2.set_ylabel("Throughput (frames/s)")
    ax2.set_ylim(0, float(np.max(fps_mean + fps_std)) * 1.25)
    ax2.spines["top"].set_visible(False)

    # Combined legend.
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False,
              ncol=2, borderpad=0.2, handlelength=1.4, columnspacing=1.0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_BASE.with_suffix(f".{ext}"), dpi=300)
    print(OUT_BASE.with_suffix(".pdf"))
    print(OUT_BASE.with_suffix(".png"))


if __name__ == "__main__":
    main()
