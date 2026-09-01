#!/usr/bin/env python3
"""
Plot direct PtychoNN SC experiment CSVs.

Usage examples:
  python experiments/plot_ptychonn_results.py --kind callback --csv <sc1.csv>
  python experiments/plot_ptychonn_results.py --kind inference --csv <sc2.csv>
  python experiments/plot_ptychonn_results.py --kind threads --csv <sc3.csv>
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mean(rows: list[dict[str, str]], key: str) -> float:
    vals = [float(r[key]) for r in rows if r.get(key) not in ("", None)]
    return float(np.mean(vals)) if vals else float("nan")


def grouped(rows: list[dict[str, str]], keys: tuple[str, ...]):
    out = defaultdict(list)
    for row in rows:
        out[tuple(row[k] for k in keys)].append(row)
    return out


def save(fig, out_base: Path) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(out_base.with_suffix(f".{ext}"), dpi=300)
    print(out_base.with_suffix(".pdf"))


def plot_callback(rows: list[dict[str, str]], out_base: Path) -> None:
    groups = grouped(rows, ("stage1_callback_batch",))
    xs = sorted(int(k[0]) for k in groups)
    labels = [str(x) for x in xs]
    e2e = [mean(groups[(str(x),)], "pipeline_e2e_s") for x in xs]
    s1 = [mean(groups[(str(x),)], "stage1_fps") for x in xs]
    s2 = [mean(groups[(str(x),)], "stage2_fps") for x in xs]

    fig, ax1 = plt.subplots(figsize=(5.0, 3.0), constrained_layout=True)
    x = np.arange(len(xs))
    ax1.plot(x, e2e, marker="o", color="#2F6B9A", linewidth=2, label="E2E latency")
    ax1.set_ylabel("Pipeline E2E latency (s)")
    ax1.set_xlabel("Stage 1 callback batch C")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.grid(True, axis="y", color="#D0D0D0", linewidth=0.7)
    ax2 = ax1.twinx()
    ax2.plot(x, s1, marker="s", color="#D28E2D", linewidth=1.8, label="Stage 1 fps")
    ax2.plot(x, s2, marker="^", color="#4C8C57", linewidth=1.8, label="Stage 2 fps")
    ax2.set_ylabel("Stage throughput (frames/s)")
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [l.get_label() for l in lines], fontsize=8)
    ax1.set_title("Callback batching with fixed inference batch")
    save(fig, out_base)


def plot_inference(rows: list[dict[str, str]], out_base: Path) -> None:
    groups = grouped(rows, ("stage1_infer_batch",))
    xs = sorted(int(k[0]) for k in groups)
    labels = [str(x) for x in xs]
    e2e = [mean(groups[(str(x),)], "pipeline_e2e_s") for x in xs]
    s1 = [mean(groups[(str(x),)], "stage1_fps") for x in xs]
    s2 = [mean(groups[(str(x),)], "stage2_fps") for x in xs]

    fig, ax1 = plt.subplots(figsize=(5.0, 3.0), constrained_layout=True)
    x = np.arange(len(xs))
    ax1.plot(x, e2e, marker="o", color="#2F6B9A", linewidth=2, label="E2E latency")
    ax1.set_ylabel("Pipeline E2E latency (s)")
    ax1.set_xlabel("TensorFlow inference batch I")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.grid(True, axis="y", color="#D0D0D0", linewidth=0.7)
    ax2 = ax1.twinx()
    ax2.plot(x, s1, marker="s", color="#D28E2D", linewidth=1.8, label="Stage 1 fps")
    ax2.plot(x, s2, marker="^", color="#4C8C57", linewidth=1.8, label="Stage 2 fps")
    ax2.set_ylabel("Stage throughput (frames/s)")
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [l.get_label() for l in lines], fontsize=8)
    ax1.set_title("Inference batching with fixed callback batch")
    save(fig, out_base)


def plot_threads(rows: list[dict[str, str]], out_base: Path) -> None:
    groups = grouped(rows, ("stage1_threads", "stage2_threads"))
    s1_vals = sorted({int(k[0]) for k in groups})
    s2_vals = sorted({int(k[1]) for k in groups})
    matrix = np.full((len(s1_vals), len(s2_vals)), np.nan)
    for i, s1 in enumerate(s1_vals):
        for j, s2 in enumerate(s2_vals):
            matrix[i, j] = mean(groups.get((str(s1), str(s2)), []), "pipeline_e2e_s")

    fig, ax = plt.subplots(figsize=(4.6, 3.6), constrained_layout=True)
    im = ax.imshow(matrix, cmap="viridis_r", aspect="auto")
    ax.set_xticks(np.arange(len(s2_vals)))
    ax.set_xticklabels([str(v) for v in s2_vals])
    ax.set_yticks(np.arange(len(s1_vals)))
    ax.set_yticklabels([str(v) for v in s1_vals])
    ax.set_xlabel("Stage 2 threads")
    ax.set_ylabel("Stage 1 threads")
    ax.set_title("Thread scaling: pipeline E2E latency")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Pipeline E2E latency (s)")
    for i in range(len(s1_vals)):
        for j in range(len(s2_vals)):
            if np.isfinite(matrix[i, j]):
                ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center",
                        color="white" if matrix[i, j] > np.nanmean(matrix) else "black",
                        fontsize=8)
    save(fig, out_base)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kind", choices=["callback", "inference", "threads"], required=True)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args()


def main():
    args = parse_args()
    rows = read_csv(args.csv)
    out_base = args.out or args.csv.with_suffix("")
    if args.kind == "callback":
        plot_callback(rows, out_base)
    elif args.kind == "inference":
        plot_inference(rows, out_base)
    else:
        plot_threads(rows, out_base)


if __name__ == "__main__":
    main()
