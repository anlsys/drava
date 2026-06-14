#!/usr/bin/env python3
"""
Generate baseline pipeline characterization visualizations.

Produces figures from the initial grid search data for paper and presentation.

Usage:
  python visualize_baseline.py [--out-dir figures/]
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Typography tuned for single-column paper inclusion.
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

# ── Data ──────────────────────────────────────────────────────────────────────

DATA = [
    # (rank, batch, s1_threads, s2_threads, cb_s1, cb_s2, rate_hz,
    #  pub_fps, s1_fps, s2_fps, e2e_s)
    (1, 256, 4, 4, 256, 64, 0.0, 16844.53, 4090.01, 1726.54, 6.41),
    (2, 256, 4, 4, 256, 32, 0.0, 17140.16, 3911.09, 1703.22, 6.45),
    (3, 512, 8, 4, 256, 32, 0.0, 15814.64, 4870.20, 1146.80, 9.42),
    (4, 256, 8, 4, 256, 64, 0.0, 16936.74, 4320.34, 1066.13, 10.06),
    (5, 512, 4, 4, 256, 64, 0.0, 16285.13, 5402.49, 1016.21, 10.48),
    (6, 256, 8, 4, 256, 32, 0.0, 16056.66, 4341.31, 941.69, 11.22),
    (7, 512, 4, 4, 256, 32, 0.0, 16041.55, 5560.56, 828.03, 12.67),
]

# Colors
C_S1 = "#3B82F6"      # blue
C_S2 = "#F59E0B"      # amber
C_E2E = "#EF4444"     # red


def config_label(row):
    """Multi-line label for x-axis."""
    _, batch, s1t, s2t, cb1, cb2, *_ = row
    return f"{batch}\n{s1t}/{s2t}\n{cb1}/{cb2}"


def config_label_short(row):
    _, batch, s1t, s2t, cb1, cb2, *_ = row
    return f"{batch}/{s1t}/{s2t}/cb{cb2}"


# ── Combined figure: throughput bars + E2E line ──────────────────────────────

def plot_combined(out_dir: Path):
    fig, ax1 = plt.subplots(figsize=(7.2, 4.8))

    labels = [config_label(r) for r in DATA]
    x = np.arange(len(DATA))
    w = 0.35

    s1_fps = [r[8] for r in DATA]
    s2_fps = [r[9] for r in DATA]
    e2e = [r[10] for r in DATA]

    # Throughput bars (left y-axis)
    ax1.bar(x - w / 2, s1_fps, w, label="Stage 1 inference", color=C_S1, alpha=0.85)
    ax1.bar(x + w / 2, s2_fps, w, label="Stage 2 stitching", color=C_S2, alpha=0.85)

    ax1.set_ylabel("Throughput (frames/s)")
    ax1.set_xlabel(r"Configuration: $B_{\mathrm{pred}}$; $N_1/N_2$; $B^{cb}_1/B^{cb}_2$",
                   labelpad=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.tick_params(axis="x", pad=8)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_axisbelow(True)

    # E2E latency line (right y-axis)
    ax2 = ax1.twinx()
    ax2.plot(x, e2e, color=C_E2E, marker="o", linewidth=3.0, markersize=8,
             label="E2E latency", zorder=5)

    for i, val in enumerate(e2e):
        ax2.text(i, val + 0.25, f"{val:.2f}s", ha="center", fontsize=13,
                 color=C_E2E, fontweight="bold")

    ax2.set_ylabel("End-to-end latency (s)", color=C_E2E)
    ax2.tick_params(axis="y", colors=C_E2E)
    ax2.set_ylim(0, max(e2e) + 1.5)

    # Combined legend
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True)

    ax1.set_title("Stage throughput vs. end-to-end latency", fontweight="bold", pad=12)

    fig.tight_layout(pad=0.7)
    for ext in ("pdf", "png"):
        path = out_dir / f"throughput_vs_latency.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [combined] {out_dir / 'throughput_vs_latency.pdf'}")


# ── Scatter: S2 FPS vs E2E ──────────────────────────────────────────────────

def plot_scatter_s2_vs_e2e(out_dir: Path):
    fig, ax = plt.subplots(figsize=(6, 5))

    s2_fps = np.array([r[9] for r in DATA])
    e2e = np.array([r[10] for r in DATA])

    ax.scatter(s2_fps, e2e, s=80, color=C_E2E, edgecolors="white", linewidth=0.8, zorder=5)

    for row in DATA:
        ax.annotate(config_label_short(row),
                     (row[9], row[10]),
                     textcoords="offset points", xytext=(8, 4),
                     fontsize=7, color="#374151")

    # Trend line
    z = np.polyfit(s2_fps, e2e, 1)
    p = np.poly1d(z)
    x_fit = np.linspace(s2_fps.min() - 50, s2_fps.max() + 50, 100)
    ax.plot(x_fit, p(x_fit), "--", color="#9CA3AF", linewidth=1, alpha=0.7)

    corr = np.corrcoef(s2_fps, e2e)[0, 1]
    ax.text(0.05, 0.95, f"$r = {corr:.3f}$",
            transform=ax.transAxes, fontsize=10, va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#D1D5DB"))

    ax.set_xlabel("Stage 2 Throughput (frames/s)", fontsize=11)
    ax.set_ylabel("End-to-End Latency $T_{e2e}$ (s)", fontsize=11)
    ax.set_title("Stage 2 Throughput vs. Pipeline Latency", fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        path = out_dir / f"scatter_s2_vs_e2e.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [scatter] {out_dir / 'scatter_s2_vs_e2e.pdf'}")


# ── Paired comparison: cb_s2=32 vs cb_s2=64 ─────────────────────────────────

def plot_paired_cb(out_dir: Path):
    C_CB64 = "#3B82F6"
    C_CB32 = "#F97316"

    groups = {}
    for row in DATA:
        _, batch, s1t, s2t, cb1, cb2, _, _, _, s2_fps, e2e = row
        key = (batch, s1t, s2t)
        if key not in groups:
            groups[key] = {}
        groups[key][cb2] = (s2_fps, e2e)

    paired = {k: v for k, v in groups.items() if 32 in v and 64 in v}
    if not paired:
        print("  [paired] No paired comparisons found, skipping.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    labels = [f"B{k[0]}/{k[1]}/{k[2]}" for k in paired]
    x = np.arange(len(paired))
    w = 0.3

    fps_32 = [v[32][0] for v in paired.values()]
    fps_64 = [v[64][0] for v in paired.values()]
    e2e_32 = [v[32][1] for v in paired.values()]
    e2e_64 = [v[64][1] for v in paired.values()]

    ax1.bar(x - w / 2, fps_32, w, label="$B_2^{cb}=32$", color=C_CB32, alpha=0.85)
    ax1.bar(x + w / 2, fps_64, w, label="$B_2^{cb}=64$", color=C_CB64, alpha=0.85)
    ax1.set_xlabel("Configuration (Batch / Threads S1/S2)", fontsize=10)
    ax1.set_ylabel("Stage 2 Throughput (fps)", fontsize=10)
    ax1.set_title("Stage 2 Throughput", fontsize=11, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_axisbelow(True)

    for i, (f32, f64) in enumerate(zip(fps_32, fps_64)):
        pct = (f64 - f32) / f32 * 100
        y_pos = max(f32, f64) + 30
        ax1.text(i, y_pos, f"+{pct:.0f}%", ha="center", fontsize=8,
                 color=C_CB64, fontweight="bold")

    ax2.bar(x - w / 2, e2e_32, w, label="$B_2^{cb}=32$", color=C_CB32, alpha=0.85)
    ax2.bar(x + w / 2, e2e_64, w, label="$B_2^{cb}=64$", color=C_CB64, alpha=0.85)
    ax2.set_xlabel("Configuration (Batch / Threads S1/S2)", fontsize=10)
    ax2.set_ylabel("End-to-End Latency (s)", fontsize=10)
    ax2.set_title("Pipeline Latency", fontsize=11, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    ax2.set_axisbelow(True)

    for i, (e32, e64) in enumerate(zip(e2e_32, e2e_64)):
        pct = (e32 - e64) / e32 * 100
        y_pos = max(e32, e64) + 0.15
        ax2.text(i, y_pos, f"-{pct:.0f}%", ha="center", fontsize=8,
                 color=C_CB64, fontweight="bold")

    fig.suptitle("Effect of Callback Batch Threshold on Stage 2",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        path = out_dir / f"paired_callback_batch.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [paired] {out_dir / 'paired_callback_batch.pdf'}")


# ── Bottleneck stacked bar ───────────────────────────────────────────────────

def plot_bottleneck_stacked(out_dir: Path):
    n_frames = 10000

    fig, ax = plt.subplots(figsize=(10, 4.5))

    data_rev = list(reversed(DATA))
    labels = [config_label_short(r) for r in data_rev]

    s1_time = [n_frames / r[8] for r in data_rev]
    s2_time = [n_frames / r[9] for r in data_rev]
    e2e_time = [r[10] for r in data_rev]

    y = np.arange(len(data_rev))
    h = 0.6

    ax.barh(y, s1_time, h, label="Stage 1 (Inference)", color=C_S1, alpha=0.85)
    ax.barh(y, s2_time, h, left=s1_time,
            label="Stage 2 (Stitching)", color=C_S2, alpha=0.85)

    for i, e in enumerate(e2e_time):
        ax.plot(e, i, "d", color=C_E2E, markersize=8, zorder=5)
    ax.plot([], [], "d", color=C_E2E, markersize=8, label="Pipeline $T_{e2e}$")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Time (s)", fontsize=11)
    ax.set_title("Pipeline Bottleneck Analysis (10,000 frames)", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)

    for i, e in enumerate(e2e_time):
        ax.text(e + 0.15, i, f"{e:.1f}s", va="center", fontsize=8, color=C_E2E)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        path = out_dir / f"bottleneck_stacked.{ext}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [stacked] {out_dir / 'bottleneck_stacked.pdf'}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate baseline visualizations")
    parser.add_argument("--out-dir", default="baseline_figures",
                        help="Output directory for figures")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating visualizations in: {out_dir}/")
    plot_combined(out_dir)
    plot_scatter_s2_vs_e2e(out_dir)
    plot_paired_cb(out_dir)
    plot_bottleneck_stacked(out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
