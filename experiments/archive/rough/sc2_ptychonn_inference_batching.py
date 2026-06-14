#!/usr/bin/env python3
"""
SC Experiment 2: PtychoNN inference batching.

Sweep TensorFlow model.predict batch size I while keeping Drava callback
batching fixed.  Results are taken directly from benchmark_two_stages.py
summary.csv; this script does not import experiments/_common.py.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PTYCHO_DIR = REPO_ROOT / "examples" / "ptychonn"
RESULTS_DIR = REPO_ROOT / "experiments" / "results"
PREDICTION_FRAMES_PER_MSG = 16


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


def read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in columns})


def latest_timestamp_dir(parent: Path) -> Path:
    dirs = sorted(p for p in parent.iterdir() if p.is_dir())
    if not dirs:
        raise RuntimeError(f"No benchmark output directory under {parent}")
    return dirs[-1]


def stage2_callback_for_frames(stage1_callback_batch: int) -> int:
    return max(1, math.ceil(stage1_callback_batch / PREDICTION_FRAMES_PER_MSG))


def run_benchmark(args, out_dir: Path, infer_batch: int) -> Path:
    if infer_batch > args.stage1_callback_batch and not args.allow_underfilled_inference:
        raise ValueError(
            f"inference batch I={infer_batch} is larger than fixed callback "
            f"batch C={args.stage1_callback_batch}; increase --stage1-callback-batch "
            f"or pass --allow-underfilled-inference"
        )
    stage2_callback_batch = (
        args.stage2_callback_batch
        if args.stage2_callback_batch is not None
        else stage2_callback_for_frames(args.stage1_callback_batch)
    )
    subdir = out_dir / f"ib{infer_batch}_cb{args.stage1_callback_batch}_s2cb{stage2_callback_batch}"
    subdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        args.python,
        "benchmark_two_stages.py",
        "--batches", str(infer_batch),
        "--stage1-threads", str(args.stage1_threads),
        "--stage2-threads", str(args.stage2_threads),
        "--stage1-callback-batch", str(args.stage1_callback_batch),
        "--stage2-callback-batch", str(stage2_callback_batch),
        "--timeout-ms", str(args.timeout_ms),
        "--rate-hz", str(args.rate_hz),
        "--num-frames", str(args.num_frames),
        "--runs", str(args.runs),
        "--out-dir", str(subdir.resolve()),
    ]
    print(f"[sc2-infer] $ cd {PTYCHO_DIR} && {' '.join(cmd)}")
    subprocess.run(cmd, cwd=PTYCHO_DIR, env=os.environ.copy(), check=True)
    return latest_timestamp_dir(subdir)


def row_from_summary(args, infer_batch: int, bench_dir: Path, srow: dict[str, str]) -> dict:
    stage2_callback_batch = (
        args.stage2_callback_batch
        if args.stage2_callback_batch is not None
        else stage2_callback_for_frames(args.stage1_callback_batch)
    )
    frames = int(float(srow["total_frames"]))
    e2e = float(srow["pipeline_e2e_s"])
    return {
        "experiment": "inference_batching",
        "run": int(srow["run"]),
        "frames": frames,
        "stage1_infer_batch": infer_batch,
        "stage1_callback_batch": args.stage1_callback_batch,
        "stage2_callback_batch": stage2_callback_batch,
        "stage2_callback_frames": stage2_callback_batch * PREDICTION_FRAMES_PER_MSG,
        "stage1_threads": args.stage1_threads,
        "stage2_threads": args.stage2_threads,
        "timeout_ms": args.timeout_ms,
        "rate_hz": args.rate_hz,
        "publisher_time_s": float(srow["publisher_time_s"]),
        "publisher_fps": float(srow["publisher_avg_fps"]),
        "stage1_time_s": float(srow["stage1_total_time_s"]),
        "stage1_fps": float(srow["stage1_total_fps"]),
        "stage2_time_s": float(srow["stage2_total_time_s"]),
        "stage2_fps": float(srow["stage2_total_fps"]),
        "pipeline_e2e_s": e2e,
        "pipeline_fps": frames / e2e if e2e > 0 else "",
        "benchmark_dir": str(bench_dir),
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--infer-batches", default="64,128,256",
                   help="Comma-separated TensorFlow model.predict batch sizes I.")
    p.add_argument("--stage1-callback-batch", type=int, default=512,
                   help="Fixed Stage 1 Drava callback batch C.")
    p.add_argument("--stage2-callback-batch", type=int, default=None,
                   help="Fixed Stage 2 callback batch in prediction messages. "
                        "Default maps Stage 1 C frames to ceil(C/16) messages.")
    p.add_argument("--allow-underfilled-inference", action="store_true")
    p.add_argument("--stage1-threads", type=int, default=4)
    p.add_argument("--stage2-threads", type=int, default=4)
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--rate-hz", type=int, default=0)
    p.add_argument("--num-frames", type=int, default=10000)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--python", default=sys.executable)
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = make_run_dir("sc2_ptychonn_inference_batching")
    rows: list[dict] = []
    for infer_batch in parse_ints(args.infer_batches):
        bench_dir = run_benchmark(args, out_dir, infer_batch)
        for srow in read_rows(bench_dir / "summary.csv"):
            rows.append(row_from_summary(args, infer_batch, bench_dir, srow))

    columns = [
        "experiment", "run", "frames",
        "stage1_infer_batch", "stage1_callback_batch",
        "stage2_callback_batch", "stage2_callback_frames",
        "stage1_threads", "stage2_threads", "timeout_ms", "rate_hz",
        "publisher_time_s", "publisher_fps",
        "stage1_time_s", "stage1_fps",
        "stage2_time_s", "stage2_fps",
        "pipeline_e2e_s", "pipeline_fps", "benchmark_dir",
    ]
    out_csv = out_dir / "sc2_inference_batching_summary.csv"
    write_rows(out_csv, rows, columns)
    print(f"[sc2-infer] wrote {len(rows)} rows -> {out_csv}")


if __name__ == "__main__":
    main()
