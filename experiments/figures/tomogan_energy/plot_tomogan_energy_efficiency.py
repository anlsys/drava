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


def main() -> None:
    rows = read_rows()
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["batch"])].append(row)

    batches = sorted(grouped)

    # Prefer full-system energy (GPU + CPU) when the summary CSV provides it
    # (populated once the benchmark is run with a working CPU energy source,
    # e.g. --cpu-energy-source perf). Fall back to GPU-only energy otherwise.
    def _has_col(col: str) -> bool:
        return all(
            col in r and r[col] not in (None, "", "None")
            for b in batches for r in grouped[b]
        )

    if _has_col("total_energy_j_per_frame"):
        energy_col = "total_energy_j_per_frame"
        energy_label = "Energy efficiency, GPU+CPU (frames/J)"
    else:
        energy_col = "gpu_energy_j_per_frame"
        energy_label = "GPU energy efficiency (frames/J)"

    # Report energy efficiency as frames per joule (higher is better) so the
    # bars share the same "higher is better" direction as the throughput line.
    efficiency_mean = [
        mean([1.0 / float(r[energy_col]) for r in grouped[b]])
        for b in batches
    ]
    efficiency_std = [
        stdev([1.0 / float(r[energy_col]) for r in grouped[b]])
        for b in batches
    ]
    fps_mean = [
        mean([float(r["stage_fps"]) for r in grouped[b]])
        for b in batches
    ]
    fps_std = [
        stdev([float(r["stage_fps"]) for r in grouped[b]])
        for b in batches
    ]

    plt.rcParams.update({
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(figsize=(3.45, 2.45), constrained_layout=True)
    x = np.arange(len(batches))
    bars = ax.bar(
        x,
        efficiency_mean,
        yerr=efficiency_std,
        width=0.62,
        capsize=3,
        color="#6A8F7A",
        edgecolor="#2E4A3A",
        linewidth=0.8,
        error_kw={"elinewidth": 0.9, "capthick": 0.9, "ecolor": "#333333"},
    )
    for bar in bars:
        bar.set_zorder(2)

    ax.set_xticks(x)
    ax.set_xticklabels([str(b) for b in batches])
    ax.set_xlabel("Callback-inference batch size")
    ax.set_ylabel(energy_label)
    ax.set_ylim(0, max(e + s for e, s in zip(efficiency_mean, efficiency_std)) * 1.18)
    ax.grid(True, axis="y", color="#D6D6D6", linewidth=0.7)
    ax.set_axisbelow(True)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax2 = ax.twinx()
    fps_mean_arr = np.asarray(fps_mean)
    fps_std_arr = np.asarray(fps_std)
    # Shaded band shows +/- 1 std across the repeated runs.
    ax2.fill_between(
        x,
        fps_mean_arr - fps_std_arr,
        fps_mean_arr + fps_std_arr,
        color="#2E5E8C",
        alpha=0.15,
        linewidth=0,
        zorder=2,
    )
    ax2.errorbar(
        x,
        fps_mean,
        yerr=fps_std,
        color="#2E5E8C",
        marker="o",
        markersize=4,
        linewidth=1.5,
        capsize=3,
        elinewidth=0.9,
        capthick=0.9,
        zorder=3,
    )
    ax2.set_ylabel("Throughput (frames/s)")
    ax2.set_ylim(0, max(fps_mean_arr + fps_std_arr) * 1.25)
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(axis="y", colors="#2E5E8C")
    ax2.yaxis.label.set_color("#2E5E8C")
    ax2.spines["right"].set_color("#2E5E8C")
    energy_proxy = plt.Line2D([0], [0], color="#6A8F7A", linewidth=6)
    throughput_proxy = plt.Line2D([0], [0], color="#2E5E8C", marker="o", linewidth=1.5)
    ax.legend(
        [energy_proxy, throughput_proxy],
        ["energy efficiency", "throughput"],
        loc="upper left",
        frameon=False,
        borderpad=0.2,
        handlelength=1.6,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_BASE.with_suffix(f".{ext}"), dpi=300)
    print(OUT_BASE.with_suffix(".pdf"))
    print(OUT_BASE.with_suffix(".png"))


if __name__ == "__main__":
    main()
