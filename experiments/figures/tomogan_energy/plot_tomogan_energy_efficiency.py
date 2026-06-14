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


HERE = Path(__file__).resolve().parent
DATA = HERE / "tomogan_energy_efficiency_data.csv"
OUT_DIR = HERE
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
    energy_mean = [
        mean([float(r["gpu_energy_j_per_frame"]) for r in grouped[b]])
        for b in batches
    ]
    energy_std = [
        stdev([float(r["gpu_energy_j_per_frame"]) for r in grouped[b]])
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
        energy_mean,
        yerr=energy_std,
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
    ax.set_ylabel("GPU energy (J/frame)")
    ax.set_ylim(0, max(e + s for e, s in zip(energy_mean, energy_std)) * 1.18)
    ax.grid(True, axis="y", color="#D6D6D6", linewidth=0.7)
    ax.set_axisbelow(True)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax2 = ax.twinx()
    ax2.plot(
        x,
        fps_mean,
        color="#2E5E8C",
        marker="o",
        markersize=4,
        linewidth=1.5,
        zorder=3,
    )
    ax2.set_ylabel("Throughput (frames/s)")
    ax2.set_ylim(0, max(fps_mean) * 1.25)
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(axis="y", colors="#2E5E8C")
    ax2.yaxis.label.set_color("#2E5E8C")
    ax2.spines["right"].set_color("#2E5E8C")
    energy_proxy = plt.Line2D([0], [0], color="#6A8F7A", linewidth=6)
    throughput_proxy = plt.Line2D([0], [0], color="#2E5E8C", marker="o", linewidth=1.5)
    ax.legend(
        [energy_proxy, throughput_proxy],
        ["GPU energy", "throughput"],
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
