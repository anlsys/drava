"""Sweep stage1 callback_batch x workload size and collect per-run metrics.

Why this exists
---------------
``runtime.callback_batch`` is the **real GPU inference batch** for this example:
``app.py:206`` takes ``n = len(frames)`` and ``_infer`` runs one
``forward_predict`` over all of them, with no sub-batching. (``DRAVA_INFER_BATCH``
sizes the *warmup* tensor only -- see ``app.py:176`` and ``NOTES.md``.) Nobody
has measured whether the current value of 128 is a good choice.

Separately, SystemFlow's fitted PtychoPINN model has coefficient rows for
``batch_size = 1024`` only, and its latency formula has **no batch-size term at
all** -- ``compute_latency_s = A_intercept + s_per_gflop * total_gflops`` is
batch-size invariant. This sweep produces the data needed to fix both gaps.

Two axes, on purpose
--------------------
Fitting ``latency = A_intercept + s_per_gflop * work`` needs several *workload*
sizes per batch size; one point per batch size gives no slope. SystemFlow's
shipped coefficients were fit from 8 points per row (the ``n`` column), so this
sweeps ``batch_size x num_frames``.

Usage
-----
    # default grid: 6 batch sizes x 6 workloads = 36 runs, ~15 min on an A100
    python sweep_callback_batch.py

    # quick check of the plumbing (no runs executed)
    python sweep_callback_batch.py --dry-run

    # custom grid
    python sweep_callback_batch.py --batches 128,512 --frames 5000,20449 --repeats 2

Writes ``run_logs/sweep_<stamp>/sweep.csv`` with one row per run, plus the
generated config and the full logs of every run. Feed that CSV to
``fit_systemflow_coefficients.py``.
"""

from __future__ import annotations

import argparse
import copy
import csv
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR.parent / "common"))

from drava_common import load_pipeline_config  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: this script needs PyYAML (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2)

DEFAULT_BATCHES = [32, 64, 128, 256, 512, 1024]
DEFAULT_FRAMES = [2000, 5000, 8000, 12000, 16000, 20449]

#: Columns copied verbatim from each run's summary.csv.
SUMMARY_COLUMNS = [
    "run", "status", "duplicates", "n_groups",
    "publisher_frames", "publisher_time_s", "publisher_avg_fps",
    "stage1_total_s", "stage1_total_fps", "stage1_compute_s",
    "stage2_total_s", "stage2_total_fps", "stage2_compute_s",
    "pipeline_e2e_s", "wall_clock_s", "nan_px_crop", "frc_auc",
]


def build_config(base: dict, batch: int, stage: str) -> dict:
    """Return a copy of ``base`` with ``stage``'s batch knobs set to ``batch``.

    ``fetch_batch`` is moved with ``callback_batch`` deliberately: for stage1 one
    NATS message is one group, so leaving fetch_batch at 128 while asking for a
    1024-frame callback would make the fetch loop, not the GPU, the thing under
    test.
    """
    cfg = copy.deepcopy(base)
    for st in cfg.get("stages", []):
        if st.get("name") != stage:
            continue
        st.setdefault("runtime", {})["callback_batch"] = batch
        st.setdefault("ingress", {})["fetch_batch"] = batch
        return cfg
    raise SystemExit(f"stage {stage!r} not found in the base pipeline config")


def read_summary(run_dir: Path) -> dict | None:
    path = run_dir / "summary.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return rows[0] if rows else None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--batches", default=",".join(map(str, DEFAULT_BATCHES)),
                   help=f"comma-separated callback_batch values (default: {DEFAULT_BATCHES})")
    p.add_argument("--frames", default=",".join(map(str, DEFAULT_FRAMES)),
                   help=f"comma-separated DRAVA_PUBLISH_NUM_FRAMES values (default: {DEFAULT_FRAMES})")
    p.add_argument("--repeats", type=int, default=1,
                   help="runs per (batch, frames) cell; >1 lets you take a median")
    p.add_argument("--stage", default="stage1", help="stage to vary (default: stage1)")
    p.add_argument("--config", default=str(EXAMPLE_DIR / "pipeline.yaml"),
                   help="base pipeline.yaml to derive from")
    p.add_argument("--out", default="", help="output dir (default: run_logs/sweep_<stamp>)")
    p.add_argument("--dry-run", action="store_true",
                   help="generate configs and print the plan without running")
    args = p.parse_args(argv)

    batches = [int(x) for x in args.batches.split(",") if x.strip()]
    frames = [int(x) for x in args.frames.split(",") if x.strip()]
    if not batches or not frames:
        p.error("--batches and --frames must be non-empty")

    base_cfg = load_pipeline_config(args.config)
    base = base_cfg.raw

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else EXAMPLE_DIR / "run_logs" / f"sweep_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = [(b, f, r) for b in batches for f in frames for r in range(args.repeats)]
    print(f"[sweep] base config : {args.config}")
    print(f"[sweep] output dir  : {out_dir}")
    print(f"[sweep] grid        : {len(batches)} batches x {len(frames)} workloads "
          f"x {args.repeats} repeat(s) = {len(plan)} runs")

    # One config per batch size; the workload varies by env var, not by config.
    cfg_paths: dict[int, Path] = {}
    for b in batches:
        path = out_dir / f"cfg_batch{b}.yaml"
        path.write_text(
            yaml.safe_dump(build_config(base, b, args.stage),
                           sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        cfg_paths[b] = path
    print(f"[sweep] wrote {len(cfg_paths)} configs")

    if args.dry_run:
        for b, f, r in plan:
            print(f"  would run batch={b:<5} frames={f:<6} repeat={r} "
                  f"cfg={cfg_paths[b].name}")
        print("[sweep] dry run: nothing executed")
        return 0

    script = EXAMPLE_DIR / "run_two_stages.sh"
    if not script.exists():
        raise SystemExit(f"missing {script}")

    results: list[dict] = []
    csv_path = out_dir / "sweep.csv"
    t0 = time.time()

    for i, (batch, nframes, rep) in enumerate(plan, 1):
        run_dir = out_dir / f"b{batch}_f{nframes}_r{rep}"
        env = dict(os.environ)
        env["DRAVA_STAGE_CONFIG"] = str(cfg_paths[batch])
        env["DRAVA_PUBLISH_NUM_FRAMES"] = str(nframes)
        env["RUN_DIR"] = str(run_dir)

        print(f"\n[sweep] ({i}/{len(plan)}) batch={batch} frames={nframes} rep={rep}")
        proc = subprocess.run([str(script)], cwd=str(EXAMPLE_DIR), env=env,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"[sweep]   FAILED rc={proc.returncode}; see {run_dir}")
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-5:]
            for line in tail:
                print(f"[sweep]   | {line}")

        summary = read_summary(run_dir)
        if summary is None:
            print("[sweep]   no summary.csv -- recording the failure and continuing")
            results.append({"callback_batch": batch, "num_frames": nframes,
                            "repeat": rep, "rc": proc.returncode, "status": "NO_SUMMARY"})
        else:
            row = {"callback_batch": batch, "num_frames": nframes, "repeat": rep,
                   "rc": proc.returncode}
            row.update({k: summary.get(k) for k in SUMMARY_COLUMNS})
            results.append(row)
            print(f"[sweep]   status={row.get('status')} "
                  f"stage1_total_s={row.get('stage1_total_s')} "
                  f"stage1_compute_s={row.get('stage1_compute_s')} "
                  f"e2e={row.get('pipeline_e2e_s')}")

        # Rewrite after every run so a crashed sweep still leaves usable data.
        fieldnames = ["callback_batch", "num_frames", "repeat", "rc"] + SUMMARY_COLUMNS
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(results)

    print(f"\n[sweep] {len(results)} runs in {time.time() - t0:.0f}s -> {csv_path}")
    _print_table(results)
    print("\nNext: python fit_systemflow_coefficients.py "
          f"{csv_path}")
    return 0


def _print_table(results: list[dict]) -> None:
    ok = [r for r in results if r.get("stage1_compute_s")]
    if not ok:
        print("[sweep] no successful runs to summarize")
        return
    print(f"\n{'batch':>6} {'frames':>7} {'stage1_wall':>12} {'stage1_compute':>15} "
          f"{'e2e':>8} {'fps':>9}")
    for r in ok:
        print(f"{r['callback_batch']:>6} {r['num_frames']:>7} "
              f"{float(r['stage1_total_s']):>12.3f} "
              f"{float(r['stage1_compute_s']):>15.3f} "
              f"{float(r['pipeline_e2e_s']):>8.3f} "
              f"{float(r['stage1_total_fps']):>9.1f}")

    print(f"\n{'batch':>6} {'median stage1 fps (all workloads)':>36}")
    by_batch: dict[int, list[float]] = {}
    for r in ok:
        by_batch.setdefault(r["callback_batch"], []).append(float(r["stage1_total_fps"]))
    best = None
    for b in sorted(by_batch):
        med = statistics.median(by_batch[b])
        best = (b, med) if best is None or med > best[1] else best
        print(f"{b:>6} {med:>36.1f}")
    if best:
        print(f"\n[sweep] highest median stage1 throughput at callback_batch={best[0]} "
              f"({best[1]:.1f} fps)")


if __name__ == "__main__":
    raise SystemExit(main())
