#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "bare_runtime_comparison.csv"
OUT_DIR = HERE


def load_rows():
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["batch"] = int(row["batch"])
        row["threads"] = int(row["threads"])
        row["pipeline_fps"] = float(row["pipeline_fps"])
        row["stage_total_fps"] = float(row["stage_total_fps"])
        row["cb_avg_ms"] = float(row["cb_avg_ms"])
    return rows


def kfps(x, _pos):
    return f"{x / 1000:.0f}k"


def main():
    rows = load_rows()
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["threads"], row["mode"])].append(row)
    for key in grouped:
        grouped[key].sort(key=lambda r: r["batch"])

    colors = {"noop": "#28666e", "cupy": "#c1662d"}
    labels = {"noop": "No-op callback", "cupy": "CuPy blank kernel"}
    markers = {"noop": "o", "cupy": "s"}
    thread_values = sorted({row["threads"] for row in rows})

    plt.rcParams.update({
        "font.size": 14,
        "axes.labelsize": 16,
        "axes.titlesize": 15,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "legend.fontsize": 12,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, axes = plt.subplots(
        2,
        len(thread_values),
        figsize=(7.2, 4.8),
        sharex=True,
        constrained_layout=True,
    )

    for col, threads in enumerate(thread_values):
        ax_fps = axes[0][col]
        ax_cb = axes[1][col]
        for mode in ("noop", "cupy"):
            series = grouped[(threads, mode)]
            batches = [row["batch"] for row in series]
            fps = [row["pipeline_fps"] for row in series]
            cb = [row["cb_avg_ms"] for row in series]
            ax_fps.plot(
                batches,
                fps,
                color=colors[mode],
                marker=markers[mode],
                linewidth=2.2,
                markersize=6,
                label=labels[mode],
            )
            ax_cb.plot(
                batches,
                cb,
                color=colors[mode],
                marker=markers[mode],
                linewidth=2.2,
                markersize=6,
            )

        ax_fps.set_title(f"{threads} runtime threads")
        ax_fps.set_xscale("log", base=2)
        ax_cb.set_xscale("log", base=2)
        ax_fps.set_ylim(0, 35000)
        ax_cb.set_ylim(0, 0.30)
        ax_fps.yaxis.set_major_formatter(FuncFormatter(kfps))
        ax_fps.grid(True, axis="y", color="#d9d9d9", linewidth=0.7)
        ax_cb.grid(True, axis="y", color="#d9d9d9", linewidth=0.7)
        ax_cb.set_xticks([8, 32, 128, 256, 512])
        ax_cb.set_xticklabels(["8", "32", "128", "256", "512"],
                              rotation=45, ha="right")

        if col == 0:
            ax_fps.set_ylabel("Pipeline throughput\n(frames/s)")
            ax_cb.set_ylabel("Callback time\n(ms/batch)")
        else:
            ax_fps.tick_params(labelleft=False)
            ax_cb.tick_params(labelleft=False)
        ax_cb.tick_params(axis="x", pad=2)

    handles, legend_labels = axes[0][0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 1.05),
    )
    fig.supxlabel("Callback batch size", fontsize=16)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "bare_runtime_ceiling.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "bare_runtime_ceiling.png", dpi=220, bbox_inches="tight")


if __name__ == "__main__":
    main()
