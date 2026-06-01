#!/usr/bin/env python3
"""
Generate agentic configuration search visualizations.

Consumes the aggregate.csv produced by tune_two_stages_ytopt.py and emits
figures for the paper:

  1. convergence.{pdf,png}        - Best-so-far E2E latency vs. evaluation index
  2. knob_importance.{pdf,png}    - Per-knob conditional minimum E2E (importance proxy)
  3. top_configs.{pdf,png}        - Parallel-coordinates of top-N configurations
  4. e2e_distribution.{pdf,png}   - Histogram of all successful evaluations vs. best

Usage:
  python visualize_agentic_search.py <aggregate.csv> [--out-dir agentic_figures/] \
                                                     [--top-n 10]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ── Colors (kept consistent with visualize_baseline.py) ───────────────────────

C_BEST = "#EF4444"        # red - best-so-far
C_EVAL = "#3B82F6"        # blue - per-evaluation
C_BAR = "#3B82F6"         # blue - bars
C_HIGHLIGHT = "#F59E0B"   # amber - highlighted choice
C_GREY = "#9CA3AF"        # grey - reference lines

# Knob columns we tune (must match SEARCH_SPACE in tune_two_stages_ytopt.py).
KNOBS: List[Tuple[str, str]] = [
    ("batch", "Batch"),
    ("stage1_threads", "S1 Threads"),
    ("stage2_threads", "S2 Threads"),
    ("stage1_callback_batch", "S1 CB"),
    ("stage2_callback_batch", "S2 CB"),
    ("rate_hz", "Rate (Hz)"),
    ("timeout_ms", "Timeout (ms)"),
]

OBJ = "pipeline_e2e_s"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_aggregate(path: Path) -> List[Dict[str, str]]:
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"No rows in {path}")
    # Filter to successful evaluations: numeric, finite, > 0 objective.
    out = []
    for r in rows:
        try:
            v = float(r[OBJ])
        except (KeyError, ValueError, TypeError):
            continue
        if not np.isfinite(v) or v <= 0:
            continue
        out.append(r)
    if not out:
        raise SystemExit(f"No successful evaluations in {path}")
    # Sort by evaluation index so convergence is meaningful.
    out.sort(key=lambda r: int(r["eval"]))
    return out


def numeric_col(rows: Sequence[Dict[str, str]], col: str) -> np.ndarray:
    return np.asarray([float(r[col]) for r in rows], dtype=float)


# ── 1. Convergence curve ─────────────────────────────────────────────────────

def plot_convergence(rows: Sequence[Dict[str, str]], out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    evals = np.asarray([int(r["eval"]) for r in rows])
    obj = numeric_col(rows, OBJ)
    best = np.minimum.accumulate(obj)

    ax.scatter(evals, obj, s=28, color=C_EVAL, alpha=0.55,
               edgecolors="white", linewidth=0.5, label="Per-evaluation $J$",
               zorder=3)
    ax.plot(evals, best, color=C_BEST, linewidth=2.0,
            label=r"Best-so-far $J^{\star}_k$", zorder=4)

    # Mark final best.
    k_star = int(np.argmin(obj))
    ax.scatter([evals[k_star]], [obj[k_star]], s=110, color=C_BEST,
               edgecolors="white", linewidth=1.2, zorder=5)
    ax.annotate(f"$J^{{\\star}} = {obj[k_star]:.2f}$ s\n@ eval {evals[k_star]}",
                (evals[k_star], obj[k_star]),
                xytext=(10, 18), textcoords="offset points",
                fontsize=10, color=C_BEST, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=C_BEST, lw=0.8))

    ax.set_xlabel("Evaluation index $k$", fontsize=12)
    ax.set_ylabel("End-to-end latency $J$ (s)", fontsize=12)
    ax.set_title("Agentic Configuration Search Convergence",
                 fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(fontsize=10, loc="upper right")

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"convergence.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [convergence] {out_dir / 'convergence.pdf'}")


# ── 2. Knob importance (conditional minimum) ─────────────────────────────────

def plot_knob_importance(rows: Sequence[Dict[str, str]], out_dir: Path) -> None:
    """For each knob, group rows by the discrete knob value and report the
    minimum observed E2E within each group. The spread across groups is a
    proxy for how strongly that knob constrains the achievable latency."""
    obj = numeric_col(rows, OBJ)
    best = float(obj.min())

    n = len(KNOBS)
    ncols = 4
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.2 * ncols, 2.8 * nrows),
                             sharey=False)
    axes = np.asarray(axes).reshape(-1)

    for ax, (col, label) in zip(axes, KNOBS):
        try:
            vals = np.asarray([float(r[col]) for r in rows])
        except (KeyError, ValueError):
            ax.set_visible(False)
            continue
        groups: Dict[float, List[float]] = {}
        for v, y in zip(vals, obj):
            groups.setdefault(v, []).append(y)
        keys = sorted(groups)
        mins = [min(groups[k]) for k in keys]

        x = np.arange(len(keys))
        # Highlight the bar corresponding to the global best.
        best_key = vals[int(np.argmin(obj))]
        colors = [C_HIGHLIGHT if k == best_key else C_BAR for k in keys]
        ax.bar(x, mins, color=colors, alpha=0.9, edgecolor="white", linewidth=0.6)

        ax.axhline(best, color=C_GREY, linestyle="--", linewidth=0.8, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels([_fmt(k) for k in keys], fontsize=8, rotation=0)
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)

    # Hide unused axes.
    for ax in axes[n:]:
        ax.set_visible(False)

    fig.text(0.005, 0.5, r"Min. observed $J$ (s)", va="center", rotation=90,
             fontsize=11)
    fig.suptitle("Per-Knob Conditional Minimum (lower = preferred setting)",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout(rect=(0.02, 0.0, 1.0, 1.0))
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"knob_importance.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [knob_importance] {out_dir / 'knob_importance.pdf'}")


# ── 3. Top-N parallel coordinates ────────────────────────────────────────────

def plot_top_configs(rows: Sequence[Dict[str, str]], out_dir: Path,
                     top_n: int) -> None:
    obj = numeric_col(rows, OBJ)
    order = np.argsort(obj)[:top_n]
    top_rows = [rows[i] for i in order]
    top_obj = obj[order]

    cols = [c for c, _ in KNOBS if c in rows[0]]
    labels = [lbl for c, lbl in KNOBS if c in rows[0]]

    # Normalize each knob column to [0, 1] using its observed range across
    # ALL evaluations (so the geometry reflects the search space we explored).
    full = {c: numeric_col(rows, c) for c in cols}
    norm_axes: List[Tuple[float, float]] = []
    for c in cols:
        v = full[c]
        lo, hi = float(v.min()), float(v.max())
        norm_axes.append((lo, hi if hi > lo else lo + 1.0))

    fig, ax = plt.subplots(figsize=(10, 5.2))

    # Color top-N by rank: best in deep blue, fading toward light grey.
    # Reserve the first colour for #1 so it stands out unambiguously.
    cmap = plt.get_cmap("viridis_r")
    for rank, (r, j) in enumerate(zip(top_rows, top_obj)):
        ys = []
        for c, (lo, hi) in zip(cols, norm_axes):
            ys.append((float(r[c]) - lo) / (hi - lo))
        if rank == 0:
            color, lw, alpha, z = C_BEST, 3.0, 1.0, 6
        else:
            color = cmap(0.2 + 0.7 * rank / max(top_n - 1, 1))
            lw, alpha, z = 1.2, 0.55, 3
        label = f"#{rank + 1}: {j:.2f} s" if rank < 3 else None
        ax.plot(np.arange(len(cols)), ys, color=color, linewidth=lw,
                alpha=alpha, label=label, zorder=z)

    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_yticks([0, 0.5, 1])
    ax.set_yticklabels(["min", "mid", "max"], fontsize=10)
    ax.set_ylim(-0.18, 1.18)
    ax.set_xlim(-0.35, len(cols) - 0.65)

    # Per-axis range labels placed in the margin, clear of the data.
    for i, (lo, hi) in enumerate(norm_axes):
        ax.text(i, -0.14, f"{_fmt(lo)}", ha="center", va="top",
                fontsize=8, color="#6B7280", style="italic")
        ax.text(i, 1.14, f"{_fmt(hi)}", ha="center", va="bottom",
                fontsize=8, color="#6B7280", style="italic")
    ax.text(-0.32, -0.14, "min:", ha="right", va="top",
            fontsize=8, color="#6B7280", style="italic")
    ax.text(-0.32, 1.14, "max:", ha="right", va="bottom",
            fontsize=8, color="#6B7280", style="italic")

    ax.set_title(f"Top-{top_n} Configurations (parallel coordinates)",
                 fontsize=13, fontweight="bold", pad=14)
    ax.grid(axis="x", alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(fontsize=10, loc="center right", framealpha=0.95,
              bbox_to_anchor=(1.0, 0.5))

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"top_configs.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [top_configs] {out_dir / 'top_configs.pdf'}")


# ── 4. Distribution of E2E latency across search ─────────────────────────────

def plot_distribution(rows: Sequence[Dict[str, str]], out_dir: Path) -> None:
    obj = numeric_col(rows, OBJ)
    best = float(obj.min())
    median = float(np.median(obj))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2),
                                   gridspec_kw={"width_ratios": [1, 1.4]})

    # Left: zoomed histogram of the optimal cluster (J <= 5s).
    near = obj[obj <= 5.0]
    ax1.hist(near, bins=np.linspace(3.8, 5.0, 13),
             color=C_EVAL, alpha=0.85, edgecolor="white")
    ax1.axvline(best, color=C_BEST, linewidth=2,
                label=fr"$J^\star = {best:.2f}$ s")
    ax1.set_xlabel("End-to-end latency $J$ (s)", fontsize=11)
    ax1.set_ylabel("Number of evaluations", fontsize=11)
    ax1.set_title(fr"Optimal cluster ($J \leq 5$ s, $n = {len(near)}$)",
                  fontsize=11, fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_axisbelow(True)
    ax1.legend(fontsize=9)
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Right: full distribution on log y-scale to expose tail.
    ax2.hist(obj, bins=np.linspace(3, 18, 31),
             color=C_EVAL, alpha=0.85, edgecolor="white")
    ax2.axvline(best, color=C_BEST, linewidth=2,
                label=fr"$J^\star = {best:.2f}$ s")
    ax2.axvline(median, color=C_GREY, linestyle="--", linewidth=1.5,
                label=fr"Median $= {median:.2f}$ s")
    ax2.set_yscale("log")
    ax2.set_xlabel("End-to-end latency $J$ (s)", fontsize=11)
    ax2.set_ylabel("Evaluations (log)", fontsize=11)
    ax2.set_title(f"Full distribution ({len(obj)} successful evals)",
                  fontsize=11, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3, which="both")
    ax2.set_axisbelow(True)
    ax2.legend(fontsize=9)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"e2e_distribution.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [distribution] {out_dir / 'e2e_distribution.pdf'}")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(v: float) -> str:
    """Compact numeric formatter for axis tick labels."""
    if float(v).is_integer():
        return f"{int(v)}"
    return f"{v:g}"


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Visualize agentic configuration search results")
    p.add_argument("aggregate", type=Path, help="Path to aggregate.csv")
    p.add_argument("--out-dir", type=Path, default=Path("agentic_figures"),
                   help="Output directory for figures")
    p.add_argument("--top-n", type=int, default=10,
                   help="Number of top configurations to plot in parallel coordinates")
    args = p.parse_args()

    rows = load_aggregate(args.aggregate)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loaded {len(rows)} successful evaluations from {args.aggregate}")
    print(f"Generating figures in: {args.out_dir}/")
    plot_convergence(rows, args.out_dir)
    plot_knob_importance(rows, args.out_dir)
    plot_top_configs(rows, args.out_dir, args.top_n)
    plot_distribution(rows, args.out_dir)
    print("Done.")


if __name__ == "__main__":
    main()
