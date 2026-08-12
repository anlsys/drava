#!/usr/bin/env python3
"""
SC Experiment 4: TomoGAN GPU energy by runtime configuration.

Run the existing TomoGAN benchmark over a batch/thread matrix with publisher
rate fixed at 0.  The underlying benchmark owns NATS startup, app execution,
GPU power sampling, and summary.csv generation; this wrapper only normalizes
the results into experiment-level raw and aggregate CSVs.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TOMOGAN_DIR = REPO_ROOT / "examples" / "tomogan"
RESULTS_DIR = REPO_ROOT / "experiments" / "results"


def parse_ints(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError(f"empty integer list: {raw!r}")
    return vals


def make_run_dir(prefix: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RESULTS_DIR / f"{prefix}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def latest_timestamp_dir(parent: Path) -> Path:
    dirs = sorted(p for p in parent.iterdir() if p.is_dir())
    if not dirs:
        raise RuntimeError(f"No benchmark output directory under {parent}")
    return dirs[-1]


def read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in columns})


def write_nats_config(path: Path, store_dir: Path) -> None:
    store = str(store_dir.resolve()).replace('"', '\\"')
    path.write_text(
        "\n".join([
            "host: 0.0.0.0",
            "port: 4222",
            "http_port: 8222",
            "max_payload: 8MB",
            "",
            "jetstream {",
            f'    store_dir: "{store}"',
            "}",
            "",
        ]),
        encoding="utf-8",
    )


def fnum(row: dict[str, str], key: str) -> float | None:
    val = row.get(key, "")
    if val in ("", None):
        return None
    return float(val)


def mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def stdev(vals: list[float]) -> float | None:
    if not vals:
        return None
    if len(vals) == 1:
        return 0.0
    mu = mean(vals)
    assert mu is not None
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(int(row["batch"]), int(row["threads"]))].append(row)

    out = []
    for (batch, threads), group in sorted(groups.items()):
        def vals(key: str) -> list[float]:
            return [float(r[key]) for r in group if r.get(key) not in ("", None)]

        gpu_jpf = vals("gpu_energy_j_per_frame")
        total_jpf = vals("total_energy_j_per_frame")
        stage_fps = vals("stage_fps")
        e2e = vals("pipeline_e2e_s")
        gpu_power = vals("gpu_avg_power_w")
        gpu_util = vals("gpu_avg_util_pct")
        out.append({
            "experiment": "tomogan_gpu_energy",
            "batch": batch,
            "threads": threads,
            "runs": len(group),
            "frames": group[0]["frames"],
            "rate_hz": group[0]["rate_hz"],
            "timeout_ms": group[0]["timeout_ms"],
            "gpu_energy_j_per_frame_mean": mean(gpu_jpf),
            "gpu_energy_j_per_frame_std": stdev(gpu_jpf),
            "total_energy_j_per_frame_mean": mean(total_jpf),
            "total_energy_j_per_frame_std": stdev(total_jpf),
            "stage_fps_mean": mean(stage_fps),
            "stage_fps_std": stdev(stage_fps),
            "pipeline_e2e_s_mean": mean(e2e),
            "pipeline_e2e_s_std": stdev(e2e),
            "gpu_avg_power_w_mean": mean(gpu_power),
            "gpu_avg_util_pct_mean": mean(gpu_util),
        })
    return out


def run_benchmark(args, out_dir: Path) -> Path:
    bench_parent = out_dir / "benchmark"
    bench_parent.mkdir(parents=True, exist_ok=True)
    nats_config = args.nats_config
    if not args.reuse_nats and nats_config is None:
        nats_config = out_dir / "nats.generated.conf"
        write_nats_config(nats_config, out_dir / "nats-store")

    cmd = [
        args.python,
        "benchmark.py",
        "--batches", args.batches,
        "--thread-list", args.thread_list,
        "--timeout-ms", str(args.timeout_ms),
        "--rate-hz", str(args.rate_hz),
        "--num-frames", str(args.num_frames),
        "--runs", str(args.runs),
        "--gpu-sample-interval-s", str(args.gpu_sample_interval_s),
        "--out-dir", str(bench_parent.resolve()),
    ]
    if args.nats_command:
        cmd.extend(["--nats-command", args.nats_command])
    if nats_config:
        cmd.extend(["--nats-config", str(nats_config.resolve())])
    if args.reuse_nats:
        cmd.append("--reuse-nats")
    if args.nats_url:
        cmd.extend(["--nats-url", args.nats_url])
    if args.stage_config:
        cmd.extend(["--stage-config", str(args.stage_config.resolve())])
    if args.no_gpu_energy:
        cmd.append("--no-gpu-energy")
    if args.rapl_glob is not None:
        cmd.extend(["--rapl-glob", args.rapl_glob])

    print(f"[sc4-tomogan-energy] $ cd {TOMOGAN_DIR} && {' '.join(cmd)}")
    subprocess.run(cmd, cwd=TOMOGAN_DIR, env=os.environ.copy(), check=True)
    return latest_timestamp_dir(bench_parent)


def row_from_benchmark(args, bench_dir: Path, srow: dict[str, str]) -> dict:
    batch = int(float(srow["batch"]))
    threads = int(float(srow["threads"]))
    frames = int(float(srow["frames"]))
    e2e = fnum(srow, "pipeline_e2e_s")
    gpu_j = fnum(srow, "gpu_energy_j")
    return {
        "experiment": "tomogan_gpu_energy",
        "config": f"b{batch}_t{threads}",
        "run": int(float(srow["run"])),
        "batch": batch,
        "threads": threads,
        "frames": frames,
        "timeout_ms": int(float(srow["timeout_ms"])),
        "rate_hz": args.rate_hz,
        "publisher_time_s": fnum(srow, "publisher_time_s"),
        "publisher_fps": fnum(srow, "publisher_avg_fps"),
        "stage_time_s": fnum(srow, "stage_time_s"),
        "stage_fps": fnum(srow, "stage_fps"),
        "cb_avg_ms": fnum(srow, "cb_avg_ms"),
        "pipeline_e2e_s": e2e,
        "pipeline_fps": frames / e2e if e2e and e2e > 0 else "",
        "drava_overhead_s": fnum(srow, "drava_overhead_s"),
        "drava_overhead_pct": fnum(srow, "drava_overhead_pct"),
        "gpu_avg_power_w": fnum(srow, "gpu_avg_power_w"),
        "gpu_avg_util_pct": fnum(srow, "gpu_avg_util_pct"),
        "gpu_avg_mem_mib": fnum(srow, "gpu_avg_mem_mib"),
        "gpu_energy_j": gpu_j,
        "gpu_energy_j_per_frame": fnum(srow, "gpu_energy_j_per_frame"),
        "cpu_rapl_energy_j": fnum(srow, "cpu_rapl_energy_j"),
        "total_energy_j": fnum(srow, "total_energy_j"),
        "total_energy_j_per_frame": fnum(srow, "total_energy_j_per_frame"),
        "benchmark_dir": str(bench_dir),
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batches", default="1,2,4,8,16",
                   help="Comma-separated TomoGAN callback/inference batch sizes.")
    p.add_argument("--thread-list", default="1,2,4,8",
                   help="Comma-separated DRAVA thread counts.")
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--rate-hz", type=int, default=0,
                   help="Publisher rate. Keep 0 for max-speed energy characterization.")
    p.add_argument("--num-frames", type=int, default=256,
                   help="Frames to publish. Uses repeated dataset frames when larger than the dataset.")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--gpu-sample-interval-s", type=float, default=0.2)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--nats-command", default="nats-server")
    p.add_argument("--nats-config", type=Path, default=None,
                   help="Optional nats-server config. By default this script generates "
                        "a clean per-experiment config with max_payload=8MB.")
    p.add_argument("--reuse-nats", action="store_true")
    p.add_argument("--nats-url", default="")
    p.add_argument("--stage-config", type=Path, default=TOMOGAN_DIR / "pipeline.yaml")
    p.add_argument("--no-gpu-energy", action="store_true")
    p.add_argument("--rapl-glob", default="/sys/class/powercap/intel-rapl:*/energy_uj",
                   help="Use '' to disable CPU/package RAPL sampling.")
    return p.parse_args()


def main():
    args = parse_args()
    parse_ints(args.batches)
    parse_ints(args.thread_list)
    if args.rate_hz != 0:
        print(f"[sc4-tomogan-energy] warning: rate_hz={args.rate_hz}; SC default is integer 0")

    out_dir = make_run_dir("sc4_tomogan_gpu_energy")
    bench_dir = run_benchmark(args, out_dir)
    rows = [row_from_benchmark(args, bench_dir, r) for r in read_rows(bench_dir / "summary.csv")]

    raw_columns = [
        "experiment", "config", "run", "batch", "threads", "frames",
        "timeout_ms", "rate_hz",
        "publisher_time_s", "publisher_fps",
        "stage_time_s", "stage_fps", "cb_avg_ms",
        "pipeline_e2e_s", "pipeline_fps",
        "drava_overhead_s", "drava_overhead_pct",
        "gpu_avg_power_w", "gpu_avg_util_pct", "gpu_avg_mem_mib",
        "gpu_energy_j", "gpu_energy_j_per_frame",
        "cpu_rapl_energy_j", "total_energy_j", "total_energy_j_per_frame",
        "benchmark_dir",
    ]
    agg_columns = [
        "experiment", "batch", "threads", "runs", "frames", "rate_hz", "timeout_ms",
        "gpu_energy_j_per_frame_mean", "gpu_energy_j_per_frame_std",
        "total_energy_j_per_frame_mean", "total_energy_j_per_frame_std",
        "stage_fps_mean", "stage_fps_std",
        "pipeline_e2e_s_mean", "pipeline_e2e_s_std",
        "gpu_avg_power_w_mean", "gpu_avg_util_pct_mean",
    ]

    raw_csv = out_dir / "sc4_tomogan_gpu_energy_summary.csv"
    agg_csv = out_dir / "sc4_tomogan_gpu_energy_aggregate.csv"
    write_rows(raw_csv, rows, raw_columns)
    write_rows(agg_csv, summarize(rows), agg_columns)
    print(f"[sc4-tomogan-energy] wrote {len(rows)} rows -> {raw_csv}")
    print(f"[sc4-tomogan-energy] wrote aggregate -> {agg_csv}")


if __name__ == "__main__":
    main()
