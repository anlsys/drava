#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import itertools
import math
import re
import subprocess
import sys
from pathlib import Path

SUMMARY_PATH_RE = re.compile(r"Logs and summary written to:\s+(?P<path>\S+)")


def parse_args():
    p = argparse.ArgumentParser(
        description="Serially sweep two-stage benchmark parameters and report the best runs."
    )
    p.add_argument("--python", default=sys.executable, help="Python executable to use.")
    p.add_argument("--benchmark-script", default="benchmark_two_stages.py",
                   help="Benchmark driver script relative to examples/ptychonn.")
    p.add_argument("--batches", default="256,512",
                   help="Comma-separated stage1 infer batch sizes.")
    p.add_argument("--stage1-threads", default="4,8,10,20",
                   help="Comma-separated stage1 DRAVA_THREADS values.")
    p.add_argument("--stage2-threads", default="1,2,4",
                   help="Comma-separated stage2 DRAVA_THREADS values.")
    p.add_argument("--stage1-callback-batches", default="256,512",
                   help="Comma-separated stage1 callback batch sizes.")
    p.add_argument("--stage2-callback-batches", default="64,128,256",
                   help="Comma-separated stage2 callback batch sizes.")
    p.add_argument("--rates", default="0",
                   help="Comma-separated publisher rate_hz values.")
    p.add_argument("--runs", type=int, default=1, help="Runs per configuration.")
    p.add_argument("--timeout-ms", type=int, default=200, help="DRAVA_FETCH_TIMEOUT_MS.")
    p.add_argument("--num-frames", type=int, default=10000, help="Frame count per run.")
    p.add_argument("--top-k", type=int, default=10, help="How many top successful runs to print.")
    p.add_argument("--objective", choices=("pipeline_e2e_s", "stage2_total_fps", "stage1_total_fps"),
                   default="pipeline_e2e_s", help="Metric to optimize.")
    p.add_argument("--keep-going", action="store_true",
                   help="Continue after failed runs instead of stopping.")
    p.add_argument("--extra-args", default="",
                   help="Extra raw args appended to benchmark_two_stages.py.")
    return p.parse_args()


def parse_int_list(raw: str):
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def parse_float_list(raw: str):
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def fmt(x, spec="{:.2f}"):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return spec.format(x)


def load_summary(summary_csv: Path):
    rows = []
    with open(summary_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        raise RuntimeError(f"No rows in summary CSV: {summary_csv}")
    row = rows[0]
    numeric_keys = {
        "batch", "run", "stage1_threads", "stage2_threads", "timeout_ms", "total_frames",
        "publisher_time_s", "publisher_avg_fps", "stage1_total_time_s", "stage1_total_fps",
        "stage2_total_time_s", "stage2_total_fps", "stage2_side", "pipeline_e2e_s",
    }
    out = {}
    for k, v in row.items():
        if k in numeric_keys and v not in ("", None):
            if k in {"batch", "run", "stage1_threads", "stage2_threads", "timeout_ms", "total_frames", "stage2_side"}:
                out[k] = int(float(v))
            else:
                out[k] = float(v)
        else:
            out[k] = v
    return out


def print_results_table(rows, objective, top_k):
    print("")
    print(
        "| Rank | Batch | Threads S1/S2 | Callback S1/S2 | Rate Hz | Publisher FPS | Stage1 FPS | Stage2 FPS | Pipeline E2E (s) | Summary |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for idx, r in enumerate(rows[:top_k], start=1):
        print(
            f"| {idx} | {r['batch']} | {r['stage1_threads']}/{r['stage2_threads']} | "
            f"{r['stage1_callback_batch']}/{r['stage2_callback_batch']} | "
            f"{fmt(r['rate_hz'])} | {fmt(r['publisher_avg_fps'])} | "
            f"{fmt(r['stage1_total_fps'])} | {fmt(r['stage2_total_fps'])} | "
            f"{fmt(r['pipeline_e2e_s'])} | {r['summary_path']} |"
        )
    print(f"\nSorted by `{objective}`.")


def _best_by_pair(rows, key_x, key_y, value_key, minimize=True):
    best = {}
    for row in rows:
        pair = (row[key_x], row[key_y])
        if pair not in best:
            best[pair] = row
            continue
        if minimize:
            if row[value_key] < best[pair][value_key]:
                best[pair] = row
        else:
            if row[value_key] > best[pair][value_key]:
                best[pair] = row
    return best


def generate_charts(rows, out_dir: Path, objective: str):
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"\nChart generation skipped: matplotlib unavailable ({exc})")
        return []

    generated = []
    minimize = objective == "pipeline_e2e_s"

    # 1. Pipeline E2E vs rate, grouped by batch.
    fig, ax = plt.subplots(figsize=(8, 5))
    batches = sorted({r["batch"] for r in rows})
    for batch in batches:
        subset = [r for r in rows if r["batch"] == batch]
        subset.sort(key=lambda r: (r["rate_hz"], r["pipeline_e2e_s"]))
        xs = [r["rate_hz"] for r in subset]
        ys = [r["pipeline_e2e_s"] for r in subset]
        ax.scatter(xs, ys, label=f"batch={batch}", alpha=0.8)
    ax.set_xlabel("Rate Hz (0 = max)")
    ax.set_ylabel("Pipeline E2E (s)")
    ax.set_title("Pipeline E2E vs Rate")
    ax.grid(True, alpha=0.3)
    ax.legend()
    path = out_dir / "pipeline_vs_rate.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(path)

    # 2. Stage FPS vs rate.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    for batch in batches:
        subset = [r for r in rows if r["batch"] == batch]
        subset.sort(key=lambda r: (r["rate_hz"], r["stage1_total_fps"]))
        xs = [r["rate_hz"] for r in subset]
        axes[0].scatter(xs, [r["stage1_total_fps"] for r in subset],
                        label=f"batch={batch}", alpha=0.8)
        axes[1].scatter(xs, [r["stage2_total_fps"] for r in subset],
                        label=f"batch={batch}", alpha=0.8)
    axes[0].set_title("Stage1 FPS vs Rate")
    axes[1].set_title("Stage2 FPS vs Rate")
    for ax in axes:
        ax.set_xlabel("Rate Hz (0 = max)")
        ax.grid(True, alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("FPS")
    path = out_dir / "stage_fps_vs_rate.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(path)

    # 3. Thread heatmap using best result per (s1_threads, s2_threads).
    thread_best = _best_by_pair(rows, "stage1_threads", "stage2_threads",
                                objective, minimize=minimize)
    s1_vals = sorted({k[0] for k in thread_best})
    s2_vals = sorted({k[1] for k in thread_best})
    grid = []
    for s2 in s2_vals:
        row_vals = []
        for s1 in s1_vals:
            entry = thread_best.get((s1, s2))
            row_vals.append(float("nan") if entry is None else entry[objective])
        grid.append(row_vals)
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(grid, aspect="auto", origin="lower")
    ax.set_xticks(range(len(s1_vals)), labels=[str(v) for v in s1_vals])
    ax.set_yticks(range(len(s2_vals)), labels=[str(v) for v in s2_vals])
    ax.set_xlabel("Stage1 Threads")
    ax.set_ylabel("Stage2 Threads")
    ax.set_title(f"Best {objective} by Thread Pair")
    for yi, s2 in enumerate(s2_vals):
        for xi, s1 in enumerate(s1_vals):
            val = grid[yi][xi]
            txt = "n/a" if math.isnan(val) else f"{val:.2f}"
            ax.text(xi, yi, txt, ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.9)
    path = out_dir / "threads_heatmap.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(path)

    # 4. Callback-batch heatmap using best result per pair.
    cb_best = _best_by_pair(rows, "stage1_callback_batch", "stage2_callback_batch",
                            objective, minimize=minimize)
    s1_cb_vals = sorted({k[0] for k in cb_best})
    s2_cb_vals = sorted({k[1] for k in cb_best})
    grid = []
    for s2_cb in s2_cb_vals:
        row_vals = []
        for s1_cb in s1_cb_vals:
            entry = cb_best.get((s1_cb, s2_cb))
            row_vals.append(float("nan") if entry is None else entry[objective])
        grid.append(row_vals)
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(grid, aspect="auto", origin="lower")
    ax.set_xticks(range(len(s1_cb_vals)), labels=[str(v) for v in s1_cb_vals])
    ax.set_yticks(range(len(s2_cb_vals)), labels=[str(v) for v in s2_cb_vals])
    ax.set_xlabel("Stage1 Callback Batch")
    ax.set_ylabel("Stage2 Callback Batch")
    ax.set_title(f"Best {objective} by Callback Pair")
    for yi, s2_cb in enumerate(s2_cb_vals):
        for xi, s1_cb in enumerate(s1_cb_vals):
            val = grid[yi][xi]
            txt = "n/a" if math.isnan(val) else f"{val:.2f}"
            ax.text(xi, yi, txt, ha="center", va="center", color="white", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.9)
    path = out_dir / "callback_heatmap.png"
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    generated.append(path)

    return generated


def main():
    args = parse_args()
    root = Path(__file__).resolve().parent
    benchmark_script = (root / args.benchmark_script).resolve()
    if not benchmark_script.exists():
        raise SystemExit(f"Benchmark script not found: {benchmark_script}")

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tuner_dir = root / "tune_logs_two_stages" / stamp
    tuner_dir.mkdir(parents=True, exist_ok=True)

    batches = parse_int_list(args.batches)
    stage1_threads_vals = parse_int_list(args.stage1_threads)
    stage2_threads_vals = parse_int_list(args.stage2_threads)
    stage1_cb_vals = parse_int_list(args.stage1_callback_batches)
    stage2_cb_vals = parse_int_list(args.stage2_callback_batches)
    rates = parse_float_list(args.rates)
    extra_args = [x for x in args.extra_args.split() if x.strip()]

    configs = list(
        itertools.product(
            batches,
            stage1_threads_vals,
            stage2_threads_vals,
            stage1_cb_vals,
            stage2_cb_vals,
            rates,
        )
    )

    results = []
    failures = []

    print(f"Running {len(configs)} configurations serially.")

    for idx, (batch, s1_threads, s2_threads, s1_cb, s2_cb, rate_hz) in enumerate(configs, start=1):
        print("")
        print(
            f"[{idx}/{len(configs)}] batch={batch} s1_threads={s1_threads} s2_threads={s2_threads} "
            f"s1_cb={s1_cb} s2_cb={s2_cb} rate_hz={rate_hz}"
        )

        cmd = [
                  args.python,
                  str(benchmark_script),
                  "--batches", str(batch),
                  "--runs", str(args.runs),
                  "--stage1-threads", str(s1_threads),
                  "--stage2-threads", str(s2_threads),
                  "--stage1-callback-batch", str(s1_cb),
                  "--stage2-callback-batch", str(s2_cb),
                  "--timeout-ms", str(args.timeout_ms),
                  "--num-frames", str(args.num_frames),
                  "--rate-hz", str(rate_hz),
              ] + extra_args

        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
        )

        run_log = tuner_dir / (
            f"run_b{batch}_s1t{s1_threads}_s2t{s2_threads}_s1cb{s1_cb}_s2cb{s2_cb}_r{str(rate_hz).replace('.', '_')}.log"
        )
        run_log.write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr, encoding="utf-8")

        print(proc.stdout, end="")
        if proc.returncode != 0:
            failures.append({
                "batch": batch,
                "stage1_threads": s1_threads,
                "stage2_threads": s2_threads,
                "stage1_callback_batch": s1_cb,
                "stage2_callback_batch": s2_cb,
                "rate_hz": rate_hz,
                "log": str(run_log),
                "error": proc.stderr.strip() or "benchmark returned non-zero",
            })
            if not args.keep_going:
                raise SystemExit(f"Benchmark failed. See {run_log}")
            continue

        m = SUMMARY_PATH_RE.search(proc.stdout)
        if not m:
            failures.append({
                "batch": batch,
                "stage1_threads": s1_threads,
                "stage2_threads": s2_threads,
                "stage1_callback_batch": s1_cb,
                "stage2_callback_batch": s2_cb,
                "rate_hz": rate_hz,
                "log": str(run_log),
                "error": "Could not find summary path in benchmark output",
            })
            if not args.keep_going:
                raise SystemExit(f"Could not find summary path. See {run_log}")
            continue

        summary_dir = Path(m.group("path"))
        summary_csv = summary_dir / "summary.csv"
        if not summary_csv.exists():
            failures.append({
                "batch": batch,
                "stage1_threads": s1_threads,
                "stage2_threads": s2_threads,
                "stage1_callback_batch": s1_cb,
                "stage2_callback_batch": s2_cb,
                "rate_hz": rate_hz,
                "log": str(run_log),
                "error": f"Missing summary CSV: {summary_csv}",
            })
            if not args.keep_going:
                raise SystemExit(f"Missing summary CSV. See {run_log}")
            continue

        row = load_summary(summary_csv)
        row["stage1_callback_batch"] = s1_cb
        row["stage2_callback_batch"] = s2_cb
        row["rate_hz"] = rate_hz
        row["summary_path"] = str(summary_dir)
        row["run_log"] = str(run_log)
        results.append(row)

    if not results:
        raise SystemExit("No successful runs collected.")

    reverse = args.objective in ("stage1_total_fps", "stage2_total_fps")
    results.sort(key=lambda r: r[args.objective], reverse=reverse)

    aggregate_csv = tuner_dir / "aggregate.csv"
    with open(aggregate_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "batch",
                "run",
                "stage1_threads",
                "stage2_threads",
                "stage1_callback_batch",
                "stage2_callback_batch",
                "rate_hz",
                "timeout_ms",
                "total_frames",
                "publisher_time_s",
                "publisher_avg_fps",
                "stage1_total_time_s",
                "stage1_total_fps",
                "stage2_total_time_s",
                "stage2_total_fps",
                "stage2_side",
                "pipeline_e2e_s",
                "summary_path",
                "run_log",
            ],
        )
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in writer.fieldnames})

    if failures:
        failures_csv = tuner_dir / "failures.csv"
        with open(failures_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "batch",
                    "stage1_threads",
                    "stage2_threads",
                    "stage1_callback_batch",
                    "stage2_callback_batch",
                    "rate_hz",
                    "log",
                    "error",
                ],
            )
            writer.writeheader()
            for row in failures:
                writer.writerow(row)
        print(f"\nRecorded {len(failures)} failures in: {failures_csv}")

    print_results_table(results, args.objective, args.top_k)
    chart_paths = generate_charts(results, tuner_dir, args.objective)
    if chart_paths:
        print("\nCharts:")
        for path in chart_paths:
            print(f"- {path}")
    print(f"\nAggregate CSV written to: {aggregate_csv}")
    print(f"Tuner logs written to: {tuner_dir}")


if __name__ == "__main__":
    main()
