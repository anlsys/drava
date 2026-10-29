"""Fit SystemFlow PtychoPINN coefficient rows from a drava sweep.

Reads the ``sweep.csv`` produced by ``sweep_callback_batch.py`` and fits, for
each ``callback_batch``, the linear model SystemFlow uses:

    compute_latency_s = A_flops_intercept_s + s_per_gflop * total_gflops
    total_gflops      = grouped_samples * F_sample_gflops * (N / baseline_N)**2

and emits a CSV in SystemFlow's own column layout
(``modeling_inference_flops_coefficients.csv``), so the rows can be handed to
the SystemFlow maintainer.

Why this and not ``systemflow.io.calibrate()``
----------------------------------------------
``calibrate()`` refines *existing* free parameters of a model **document** to
match observations. It cannot add a batch-size dimension that the model does not
have: SystemFlow's PtychoPINN latency formula has no batch-size term, and its
coefficient table is keyed ``(gpu, batch_size)`` with only ``1024`` present.
Adding rows is a *fitting* job, not a calibration job -- it reproduces the
procedure that generated the shipped row. Use ``calibrate()`` for the other
case: tuning analytic knobs such as ``"op latency (s)"`` or ``"parallelism (%)"``
inside a model document. See ``docs/systemflow.md``.

Caveat you must decide on
-------------------------
Which measured column corresponds to SystemFlow's ``compute_latency_s`` is a
**modelling choice, not a fact**. SystemFlow's PtychoPINN coefficients were fit
on a batch inference script, not a streaming two-stage pipeline:

  --latency-column stage1_compute_s  (default) total GPU callback time. Closest
      to "time spent doing inference", but it is summed across concurrent
      callbacks when callback_serialize is false.
  --latency-column stage1_total_s    stage1 wall time. Throughput-relevant, but
      includes transport waits and overlaps with the publisher.

Run it both ways and report both. Do not silently pick one.

Usage
-----
    python fit_systemflow_coefficients.py run_logs/sweep_<stamp>/sweep.csv
    python fit_systemflow_coefficients.py sweep.csv --latency-column stage1_total_s
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# SystemFlow's shipped PtychoPINN assumptions (xrs_model_data/ptychopinn/).
F_SAMPLE_GFLOPS = 1.67
BASELINE_N = 64

LATENCY_COLUMNS = ("stage1_compute_s", "stage1_total_s", "pipeline_e2e_s")


def linfit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Least-squares fit y = a + b*x. Returns (intercept, slope, r2)."""
    n = len(xs)
    if n < 2:
        raise ValueError("need at least 2 points")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        raise ValueError("all x values identical; vary the workload size")
    b = sxy / sxx
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return a, b, r2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("sweep_csv", help="sweep.csv from sweep_callback_batch.py")
    p.add_argument("--gpu", default="A100", help="GPU label for the output rows")
    p.add_argument("--resolution", type=int, default=64, help="patch side N")
    p.add_argument("--latency-column", default="stage1_compute_s",
                   choices=LATENCY_COLUMNS,
                   help="measured column treated as SystemFlow compute_latency_s")
    p.add_argument("--out", default="", help="write the coefficient CSV here")
    args = p.parse_args(argv)

    path = Path(args.sweep_csv)
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return 1

    with path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("status") == "complete"
                or (r.get("status") == "capped" and r.get("stage1_compute_s"))]

    if not rows:
        print("no usable rows (need status=complete or capped with metrics)",
              file=sys.stderr)
        return 1

    scale = (args.resolution / BASELINE_N) ** 2
    by_batch: dict[int, list[tuple[float, float]]] = {}
    for r in rows:
        try:
            groups = float(r["publisher_frames"])
            lat = float(r[args.latency_column])
            batch = int(r["callback_batch"])
        except (KeyError, TypeError, ValueError):
            continue
        total_gflops = groups * F_SAMPLE_GFLOPS * scale
        by_batch.setdefault(batch, []).append((total_gflops, lat))

    print(f"source        : {path}")
    print(f"latency column: {args.latency_column}")
    print(f"resolution    : {args.resolution}x{args.resolution} "
          f"(work scale {scale:g})\n")

    print(f"{'batch':>6} {'n':>3} {'A_intercept_s':>14} {'s_per_gflop':>13} "
          f"{'ms_per_tflop':>13} {'P_eff_tflops':>13} {'r2':>7}")

    out_rows = []
    for batch in sorted(by_batch):
        pts = by_batch[batch]
        if len(pts) < 2:
            print(f"{batch:>6} {len(pts):>3}   skipped: need >=2 workload sizes")
            continue
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        a, b, r2 = linfit(xs, ys)
        ms_per_tflop = b * 1000.0 * 1000.0   # s/GFLOP -> ms/TFLOP
        p_eff = (1.0 / b / 1000.0) if b > 0 else float("nan")  # TFLOP/s
        print(f"{batch:>6} {len(pts):>3} {a:>14.4f} {b:>13.6g} "
              f"{ms_per_tflop:>13.4f} {p_eff:>13.4f} {r2:>7.4f}")
        out_rows.append({
            "gpu": args.gpu,
            "batch_size": batch,
            "baseline_N": BASELINE_N,
            "F_sample_gflops": F_SAMPLE_GFLOPS,
            "A_flops_intercept_s": round(a, 6),
            "s_per_gflop": f"{b:.8g}",          # full precision on purpose
            "ms_per_tflop_work": round(ms_per_tflop, 4),
            "P_eff_tflops": round(p_eff, 4),
            "flops_model_r2": round(r2, 4),
            "n": len(pts),
        })

    if not out_rows:
        print("\nnothing fitted", file=sys.stderr)
        return 1

    print("\nNote: s_per_gflop is emitted at full precision. SystemFlow's shipped "
          "A100 row\nrounds it to 0.0, which zeroes the workload term; do not "
          "round this column.")

    best = max(out_rows, key=lambda r: r["P_eff_tflops"])
    print(f"\nHighest effective throughput: batch_size={best['batch_size']} "
          f"at {best['P_eff_tflops']:.2f} TFLOP/s")
    if any(abs(r["P_eff_tflops"] - out_rows[0]["P_eff_tflops"]) > 1e-9
           for r in out_rows):
        print("Latency DOES depend on batch size -> SystemFlow's batch-invariant "
              "formula is incomplete, and these rows are the evidence.")

    out = Path(args.out) if args.out else path.with_name(
        "modeling_inference_flops_coefficients_drava.csv")
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nwrote {out}")
    print("Send this to the SystemFlow maintainer; do not edit the system_flow "
          "checkout directly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
