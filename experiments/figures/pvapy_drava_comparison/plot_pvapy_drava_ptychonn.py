#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import shutil


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CSV_PATH = HERE / "pvapy_drava_ptychonn.csv"
FIGS_DIR = REPO_ROOT / "figures"


def load_rows() -> list[dict[str, object]]:
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["rate_label"] = row["rate_hz"]
        row["rate_value"] = 24000.0 if row["rate_hz"] == "max" else float(row["rate_hz"])
        row["batch"] = int(row["batch"])
        row["num_frames"] = int(row["num_frames"])
        row["publisher_fps"] = float(row["publisher_fps"])
        row["rx_items"] = int(row["rx_items"])
        row["expected_frames"] = int(row["expected_frames"])
        row["missed_frames"] = int(row["missed_frames"])
        row["loss_pct"] = 100.0 * row["missed_frames"] / row["expected_frames"]
        row["stage_total_s"] = float(row["stage_total_s"])
        row["stage_total_fps"] = float(row["stage_total_fps"])
        row["valid_stage_fps"] = row["valid_stage_fps"] == "1"
    return rows


def fmt_k(x, _pos):
    if x >= 1000:
        return f"{x / 1000:g}k"
    return f"{x:g}"


def best_loss_free_by_runtime_rate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    best: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        if not row["valid_stage_fps"] or row["missed_frames"] != 0:
            continue
        key = (str(row["runtime"]), str(row["rate_label"]))
        old = best.get(key)
        if old is None or row["stage_total_fps"] > old["stage_total_fps"]:
            best[key] = row
    return sorted(best.values(), key=lambda row: (str(row["runtime"]), row["rate_value"]))


def main() -> None:
    rows = load_rows()
    plot_rows = best_loss_free_by_runtime_rate(rows)
    colors = {"Drava": "#27667B", "PvaPy": "#C1662D"}
    markers = {"Drava": "o", "PvaPy": "s"}

    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 11,
        "axes.titlesize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, ax = plt.subplots(1, 1, figsize=(5.0, 3.0), constrained_layout=True)

    x_positions = {"1000": 0, "2000": 1, "2500": 2, "3000": 3, "max": 4}
    x_labels = ["1k", "2k", "2.5k", "3k", "max"]

    for runtime in ("PvaPy", "Drava"):
        series = [
            row for row in plot_rows
            if row["runtime"] == runtime and str(row["rate_label"]) in x_positions
        ]
        series.sort(key=lambda row: x_positions[str(row["rate_label"])])
        ax.plot(
            [x_positions[str(row["rate_label"])] for row in series],
            [row["stage_total_fps"] for row in series],
            color=colors[runtime],
            marker=markers[runtime],
            linewidth=2.4,
            markersize=6.5,
            label=runtime,
        )

    ax.annotate(
        "unpaced",
        xy=(x_positions["max"], 2817.91),
        xytext=(-4, -22),
        textcoords="offset points",
        ha="center",
        fontsize=8,
        color=colors["Drava"],
    )

    ax.set_title("Best loss-free PtychoNN stage throughput")
    ax.set_ylabel("Stage throughput (frames/s)")
    ax.set_xlabel("Publisher rate")
    ax.set_xticks(list(range(len(x_labels))))
    ax.set_xticklabels(x_labels)
    ax.set_ylim(350, 3150)
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_k))
    ax.grid(True, axis="y", color="#D3D3D3", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", frameon=False)

    out_pdf = HERE / "pvapy_drava_ptychonn.pdf"
    out_png = HERE / "pvapy_drava_ptychonn.png"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=300, bbox_inches="tight")

    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_pdf, FIGS_DIR / out_pdf.name)
    shutil.copy2(out_png, FIGS_DIR / out_png.name)
    print(out_pdf)
    print(FIGS_DIR / out_pdf.name)


if __name__ == "__main__":
    main()
