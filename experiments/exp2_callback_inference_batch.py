#!/usr/bin/env python3
"""
Experiment 2: Decoupling Callback Batch and Inference Batch
===========================================================

Goal
----
Measure why Drava exposes callback batching separately from the application
inference batch. Callback batching controls how many transport messages Drava
collects before invoking the Python callback; inference batching controls the
maximum tensor batch passed to TensorFlow/Keras inside that callback.

Workload
--------
PtychoNN two-stage pipeline:
  * Stage 1: TensorFlow/Keras GPU inference
  * Stage 2: CPU NumPy stitching

Execution model
---------------
For each pair (C, I):
  * Drava calls Stage 1 once per C raw frames, via DRAVA_STAGE1_CALLBACK_BATCH.
  * Stage 1 splits each callback into TensorFlow inference chunks of at most I
    frames, via DRAVA_INFER_BATCH.
  * Stage 1 publishes prediction payloads downstream in fixed 16-frame chunks.
  * Stage 2 callback batching is held fixed to avoid conflating Stage 1 tuning
    with downstream callback policy.

Sweep
-----
* stage1_callback_batch C over {64, 128, 256, 512}
* stage1_infer_batch    I over {64, 128, 256}
* by default, only C >= I pairs are run so each callback contains at least one
  full inference batch. Use --allow-underfilled-inference to include C < I.
* Stage 2 callback batch fixed at 8 prediction messages by default
  (8 messages * 16 predicted frames/message = 128 frames worth of predictions).
* publisher rate = 0 (max speed)

Outputs
-------
experiments/results/exp2_cb_infer_<ts>/exp2_cb_infer_summary.csv

Required runtime changes: NONE.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    LatencyDecomp,
    make_run_dir,
    parse_metrics_from_log,
    read_summary_csv,
    run_ptychonn_benchmark,
    write_rows,
)


def parse_ints(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError(f"empty integer list: {raw!r}")
    return vals


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--callback-batches", default="64,128,256,512",
                   help="Comma-separated Stage 1 Drava callback batch sizes C.")
    p.add_argument("--infer-batches", default="64,128,256",
                   help="Comma-separated Stage 1 TensorFlow inference batch sizes I.")
    p.add_argument("--allow-underfilled-inference", action="store_true",
                   help="Also run C < I pairs; TensorFlow then receives C-frame chunks.")
    p.add_argument("--stage2-callback-batch", type=int, default=8,
                   help="Stage 2 callback batch in prediction messages.")
    p.add_argument("--stage1-threads", type=int, default=4)
    p.add_argument("--stage2-threads", type=int, default=4)
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--rate-hz", type=float, default=0.0)
    p.add_argument("--num-frames", type=int, default=10000)
    p.add_argument("--runs", type=int, default=1)
    return p.parse_args()


def valid_pairs(callback_batches: list[int],
                infer_batches: list[int],
                allow_underfilled: bool) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for cb in callback_batches:
        for ib in infer_batches:
            if cb < ib and not allow_underfilled:
                continue
            pairs.append((cb, ib))
    return pairs


def estimate_predict_calls(frames: int, callback_batch: int, infer_batch: int) -> int | None:
    if frames <= 0 or callback_batch <= 0 or infer_batch <= 0:
        return None
    full_callbacks, remainder = divmod(frames, callback_batch)
    per_full_callback = math.ceil(callback_batch / infer_batch)
    calls = full_callbacks * per_full_callback
    if remainder:
        calls += math.ceil(remainder / infer_batch)
    return calls


def collect_pair(args, run_dir: Path, callback_batch: int, infer_batch: int) -> list[dict]:
    tag = f"cb{callback_batch}_ib{infer_batch}"
    ts = run_ptychonn_benchmark(
        run_dir / tag,
        batches=[infer_batch],
        stage1_threads=args.stage1_threads,
        stage2_threads=args.stage2_threads,
        stage1_callback_batch=callback_batch,
        stage2_callback_batch=args.stage2_callback_batch,
        timeout_ms=args.timeout_ms,
        rate_hz=args.rate_hz,
        num_frames=args.num_frames,
        runs=args.runs,
        extra_env={
            "DRAVA_STAGE1_CALLBACK_BATCH": str(callback_batch),
            "DRAVA_INFER_BATCH": str(infer_batch),
        },
    )

    rows: list[dict] = []
    summary = read_summary_csv(ts / "summary.csv")
    for srow in summary:
        run = int(srow["run"])
        log_s1 = ts / f"app_stage1_b{infer_batch}_r{run}.log"
        log_s2 = ts / f"app_stage2_b{infer_batch}_r{run}.log"
        m1 = parse_metrics_from_log(log_s1)
        m2 = parse_metrics_from_log(log_s2)

        frames = int(srow.get("total_frames") or 0)
        e2e = float(srow.get("pipeline_e2e_s") or 0.0) or None
        d1 = LatencyDecomp.from_stage(m1, e2e) if m1 else LatencyDecomp(end_to_end_s=e2e)
        d2 = LatencyDecomp.from_stage(m2, e2e) if m2 else LatencyDecomp(end_to_end_s=e2e)

        pipeline_fps = frames / e2e if e2e and e2e > 0 else None
        s1_cb_batches = m1.cb_batches if m1 else None
        avg_frames_per_callback = (
            frames / s1_cb_batches if s1_cb_batches and s1_cb_batches > 0 else None
        )
        predict_calls_est = estimate_predict_calls(frames, callback_batch, infer_batch)
        predicts_per_callback_est = (
            math.ceil(callback_batch / infer_batch) if infer_batch > 0 else None
        )

        rows.append({
            "workload": "ptychonn",
            "run": run,
            "frames": frames,
            "stage1_callback_batch": callback_batch,
            "stage1_infer_batch": infer_batch,
            "stage2_callback_batch": args.stage2_callback_batch,
            "stage1_threads": args.stage1_threads,
            "stage2_threads": args.stage2_threads,
            "timeout_ms": args.timeout_ms,
            "rate_hz": args.rate_hz,
            "pipeline_e2e_s": e2e,
            "pipeline_fps": pipeline_fps,
            "publisher_fps": float(srow.get("publisher_avg_fps") or 0.0) or None,
            "stage1_fps": float(srow.get("stage1_total_fps") or 0.0) or None,
            "stage2_fps": float(srow.get("stage2_total_fps") or 0.0) or None,
            "stage1_cb_batches": s1_cb_batches,
            "stage1_avg_frames_per_callback": avg_frames_per_callback,
            "stage1_predict_calls_est": predict_calls_est,
            "stage1_predicts_per_callback_est": predicts_per_callback_est,
            "stage1_tx_msgs": m1.tx_msgs if m1 else None,
            "stage1_tx_bytes": m1.tx_bytes if m1 else None,
            "stage1_cb_avg_ms": m1.cb_avg_ms if m1 else None,
            "stage1_callback_compute_s": d1.callback_compute_s,
            "stage1_publish_s": d1.publish_s,
            "stage1_dispatch_overhead_s": d1.dispatch_overhead_s,
            "stage1_transport_lumped_s": d1.transport_lumped_s,
            "stage2_cb_batches": m2.cb_batches if m2 else None,
            "stage2_cb_avg_ms": m2.cb_avg_ms if m2 else None,
            "stage2_dispatch_overhead_s": d2.dispatch_overhead_s,
            "stage2_transport_lumped_s": d2.transport_lumped_s,
            "notes": (
                "underfilled_inference_chunks"
                if callback_batch < infer_batch else ""
            ),
        })
    return rows


def main():
    args = parse_args()
    run_dir = make_run_dir("exp2_cb_infer")
    print(f"[exp2-cb-infer] writing to {run_dir}")

    callback_batches = parse_ints(args.callback_batches)
    infer_batches = parse_ints(args.infer_batches)
    pairs = valid_pairs(
        callback_batches,
        infer_batches,
        args.allow_underfilled_inference,
    )
    if not pairs:
        raise SystemExit("No valid (callback_batch, infer_batch) pairs to run.")

    rows: list[dict] = []
    for callback_batch, infer_batch in pairs:
        print(
            f"[exp2-cb-infer] pair callback_batch={callback_batch} "
            f"infer_batch={infer_batch}"
        )
        rows.extend(collect_pair(args, run_dir, callback_batch, infer_batch))

    cols = [
        "workload", "run", "frames",
        "stage1_callback_batch", "stage1_infer_batch", "stage2_callback_batch",
        "stage1_threads", "stage2_threads", "timeout_ms", "rate_hz",
        "pipeline_e2e_s", "pipeline_fps", "publisher_fps",
        "stage1_fps", "stage2_fps",
        "stage1_cb_batches", "stage1_avg_frames_per_callback",
        "stage1_predict_calls_est", "stage1_predicts_per_callback_est",
        "stage1_tx_msgs", "stage1_tx_bytes", "stage1_cb_avg_ms",
        "stage1_callback_compute_s", "stage1_publish_s",
        "stage1_dispatch_overhead_s", "stage1_transport_lumped_s",
        "stage2_cb_batches", "stage2_cb_avg_ms",
        "stage2_dispatch_overhead_s", "stage2_transport_lumped_s",
        "notes",
    ]
    out = run_dir / "exp2_cb_infer_summary.csv"
    write_rows(out, rows, cols)
    print(f"[exp2-cb-infer] wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
