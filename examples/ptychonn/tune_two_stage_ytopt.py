#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import math
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

SUMMARY_PATH_RE = re.compile(r"Logs and summary written to:\s+(?P<path>\S+)")


def parse_args():
    p = argparse.ArgumentParser(
        description="Tune PtychoNN two-stage benchmark parameters with ytopt ask/tell."
    )
    p.add_argument("--python", default=sys.executable, help="Python executable to use.")
    p.add_argument("--benchmark-script", default="benchmark_two_stages.py",
                   help="Benchmark driver script relative to examples/ptychonn.")
    p.add_argument("--batches", default="256,512",
                   help="Comma-separated stage1 infer batch sizes to search.")
    p.add_argument("--stage1-threads", default="4,8,10,20",
                   help="Comma-separated stage1 DRAVA_THREADS values to search.")
    p.add_argument("--stage2-threads", default="1,2,4",
                   help="Comma-separated stage2 DRAVA_THREADS values to search.")
    p.add_argument("--stage1-callback-batches", default="256,512",
                   help="Comma-separated stage1 callback batch sizes to search.")
    p.add_argument("--stage2-callback-batches", default="64,128,256",
                   help="Comma-separated stage2 callback batch sizes to search.")
    p.add_argument("--rates", default="0",
                   help="Comma-separated integer publisher rate_hz values to search.")
    p.add_argument("--runs", type=int, default=1, help="Runs per benchmark evaluation.")
    p.add_argument("--timeout-ms", type=int, default=200,
                   help="Fixed DRAVA_FETCH_TIMEOUT_MS used when --timeouts-ms is not set.")
    p.add_argument("--timeouts-ms", default=None,
                   help="Comma-separated DRAVA_FETCH_TIMEOUT_MS values to search.")
    p.add_argument("--num-frames", type=int, default=10000, help="Frame count per run.")
    p.add_argument("--max-evals", type=int, default=24, help="Maximum ytopt evaluations.")
    p.add_argument("--initial-points", type=int, default=8,
                   help="Initial random/model-seeding points before ytopt refits.")
    p.add_argument("--batch-size", type=int, default=1,
                   help="Number of points to ask before each ytopt tell.")
    p.add_argument("--top-k", type=int, default=10, help="How many top successful runs to print.")
    p.add_argument("--objective", choices=("pipeline_e2e_s", "stage2_total_fps", "stage1_total_fps"),
                   default="pipeline_e2e_s", help="Metric to optimize.")
    p.add_argument("--failure-penalty", type=float, default=1.0e30,
                   help="Objective value reported to ytopt for failed benchmark runs.")
    p.add_argument("--learner", choices=("RF", "ET", "GBRT", "GP", "DUMMY"), default="RF",
                   help="ytopt/scikit-optimize surrogate model.")
    p.add_argument("--liar-strategy", choices=("cl_min", "cl_mean", "cl_max"), default="cl_max",
                   help="ytopt constant-liar strategy for batched asks.")
    p.add_argument("--acq-func", choices=("LCB", "EI", "PI", "gp_hedge"), default="gp_hedge",
                   help="ytopt acquisition function.")
    p.add_argument("--kappa", type=float, default=1.96, help="LCB acquisition kappa.")
    p.add_argument("--seed", type=int, default=2345, help="ytopt random seed.")
    p.add_argument("--extra-args", default="",
                   help="Extra raw args appended to benchmark_two_stages.py.")
    return p.parse_args()


def parse_int_list(raw: str):
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise SystemExit(f"Expected at least one integer in: {raw!r}")
    return vals


def fmt(x, spec="{:.2f}"):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return spec.format(x)


def normalize_point(point):
    return {
        "batch": int(point["batch"]),
        "stage1_threads": int(point["stage1_threads"]),
        "stage2_threads": int(point["stage2_threads"]),
        "stage1_callback_batch": int(point["stage1_callback_batch"]),
        "stage2_callback_batch": int(point["stage2_callback_batch"]),
        "rate_hz": int(point["rate_hz"]),
        "timeout_ms": int(point["timeout_ms"]),
    }


def load_summary(summary_csv: Path):
    with open(summary_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError(f"No rows in summary CSV: {summary_csv}")

    numeric_keys = {
        "batch", "run", "stage1_threads", "stage2_threads", "timeout_ms", "total_frames",
        "publisher_time_s", "publisher_avg_fps", "stage1_total_time_s", "stage1_total_fps",
        "stage2_total_time_s", "stage2_total_fps", "stage2_side", "pipeline_e2e_s",
    }
    out = {}
    for k, v in rows[0].items():
        if k in numeric_keys and v not in ("", None):
            if k in {"batch", "run", "stage1_threads", "stage2_threads", "timeout_ms", "total_frames", "stage2_side"}:
                out[k] = int(float(v))
            else:
                out[k] = float(v)
        else:
            out[k] = v
    return out


def objective_value(row, objective, failure_penalty):
    if row is None or row.get(objective) in (None, ""):
        return failure_penalty
    value = float(row[objective])
    if not math.isfinite(value):
        return failure_penalty
    return -value if objective in {"stage1_total_fps", "stage2_total_fps"} else value


def import_ytopt_bits():
    try:
        import ConfigSpace as CS
        import ConfigSpace.hyperparameters as CSH
        from ytopt.search.optimizer import Optimizer
    except Exception as exc:
        raise SystemExit(
            "Missing ytopt dependencies. Install them with:\n"
            "  python -m pip install -r requirements-ytopt.txt\n"
            f"Import error: {exc}"
        ) from exc
    return CS, CSH, Optimizer


def build_search_space(args):
    CS, CSH, _ = import_ytopt_bits()
    cs = CS.ConfigurationSpace(seed=args.seed)
    hyperparameters = [
        CSH.CategoricalHyperparameter("batch", choices=parse_int_list(args.batches)),
        CSH.CategoricalHyperparameter("stage1_threads", choices=parse_int_list(args.stage1_threads)),
        CSH.CategoricalHyperparameter("stage2_threads", choices=parse_int_list(args.stage2_threads)),
        CSH.CategoricalHyperparameter(
            "stage1_callback_batch",
            choices=parse_int_list(args.stage1_callback_batches),
        ),
        CSH.CategoricalHyperparameter(
            "stage2_callback_batch",
            choices=parse_int_list(args.stage2_callback_batches),
        ),
        CSH.CategoricalHyperparameter("rate_hz", choices=parse_int_list(args.rates)),
        CSH.CategoricalHyperparameter(
            "timeout_ms",
            choices=parse_int_list(args.timeouts_ms) if args.timeouts_ms else [args.timeout_ms],
        ),
    ]
    if hasattr(cs, "add"):
        cs.add(hyperparameters)
    else:
        cs.add_hyperparameters(hyperparameters)
    return cs


def patch_skopt_categorical_imputer(ytoptimizer):
    """Work around skopt/sklearn categorical int imputation on newer sklearn.

    ytopt stores ConfigSpace categorical choices in skopt. With integer
    categorical values, skopt's inverse-transform path can ask sklearn to
    impute an int64 array using fill_value=np.nan, which newer sklearn rejects.
    This search space has no conditional inactive dimensions, so a zero fill
    value is enough to keep skopt's internal bookkeeping from crashing while
    preserving the categorical values that ytopt returns.
    """
    skopt_space = getattr(getattr(ytoptimizer, "_optimizer", None), "space", None)
    if skopt_space is None:
        return
    for attr in ("imp_const", "imp_const_inv"):
        imputer = getattr(skopt_space, attr, None)
        if imputer is not None and hasattr(imputer, "fill_value"):
            imputer.fill_value = 0


def forget_ytopt_point(ytoptimizer, point):
    key = ytoptimizer.make_key(point.values())
    if key in ytoptimizer.evals:
        del ytoptimizer.evals[key]
        ytoptimizer.counter -= 1


def run_benchmark(root: Path, benchmark_script: Path, tuner_dir: Path, args, point, eval_idx: int):
    point = normalize_point(point)
    rate_slug = str(point["rate_hz"]).replace(".", "_")
    run_log = tuner_dir / (
        f"eval{eval_idx:04d}_b{point['batch']}_s1t{point['stage1_threads']}_"
        f"s2t{point['stage2_threads']}_s1cb{point['stage1_callback_batch']}_"
        f"s2cb{point['stage2_callback_batch']}_r{rate_slug}_to{point['timeout_ms']}.log"
    )
    cmd = [
              args.python,
              str(benchmark_script),
              "--batches", str(point["batch"]),
              "--runs", str(args.runs),
              "--stage1-threads", str(point["stage1_threads"]),
              "--stage2-threads", str(point["stage2_threads"]),
              "--stage1-callback-batch", str(point["stage1_callback_batch"]),
              "--stage2-callback-batch", str(point["stage2_callback_batch"]),
              "--timeout-ms", str(point["timeout_ms"]),
              "--num-frames", str(args.num_frames),
              "--rate-hz", str(point["rate_hz"]),
          ] + shlex.split(args.extra_args)

    started = time.monotonic()
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    elapsed_s = time.monotonic() - started
    run_log.write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        return None, {
            **point,
            "eval": eval_idx,
            "log": str(run_log),
            "error": proc.stderr.strip() or "benchmark returned non-zero",
            "elapsed_s": elapsed_s,
        }

    match = SUMMARY_PATH_RE.search(proc.stdout)
    if not match:
        return None, {
            **point,
            "eval": eval_idx,
            "log": str(run_log),
            "error": "Could not find summary path in benchmark output",
            "elapsed_s": elapsed_s,
        }

    summary_dir = Path(match.group("path"))
    summary_csv = summary_dir / "summary.csv"
    if not summary_csv.exists():
        return None, {
            **point,
            "eval": eval_idx,
            "log": str(run_log),
            "error": f"Missing summary CSV: {summary_csv}",
            "elapsed_s": elapsed_s,
        }

    row = load_summary(summary_csv)
    row.update(point)
    row["eval"] = eval_idx
    row["summary_path"] = str(summary_dir)
    row["run_log"] = str(run_log)
    row["ytopt_eval_elapsed_s"] = elapsed_s
    return row, None


def write_csv(path: Path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def print_results_table(rows, objective, top_k):
    print("")
    print(
        "| Rank | Eval | Batch | Threads S1/S2 | Callback S1/S2 | Rate Hz | Timeout ms | Publisher FPS | Stage1 FPS | Stage2 FPS | Pipeline E2E (s) | Summary |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for idx, row in enumerate(rows[:top_k], start=1):
        print(
            f"| {idx} | {row['eval']} | {row['batch']} | "
            f"{row['stage1_threads']}/{row['stage2_threads']} | "
            f"{row['stage1_callback_batch']}/{row['stage2_callback_batch']} | "
            f"{fmt(row['rate_hz'])} | {row['timeout_ms']} | {fmt(row.get('publisher_avg_fps'))} | "
            f"{fmt(row.get('stage1_total_fps'))} | {fmt(row.get('stage2_total_fps'))} | "
            f"{fmt(row.get('pipeline_e2e_s'))} | {row['summary_path']} |"
        )
    direction = "descending" if objective in {"stage1_total_fps", "stage2_total_fps"} else "ascending"
    print(f"\nSorted by `{objective}` ({direction}).")


def main():
    args = parse_args()
    if args.max_evals < 1:
        raise SystemExit("--max-evals must be positive.")
    if args.initial_points < 1:
        raise SystemExit("--initial-points must be positive.")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive.")

    root = Path(__file__).resolve().parent
    benchmark_script = (root / args.benchmark_script).resolve()
    if not benchmark_script.exists():
        raise SystemExit(f"Benchmark script not found: {benchmark_script}")

    _, _, Optimizer = import_ytopt_bits()
    search_space = build_search_space(args)
    ytoptimizer = Optimizer(
        num_workers=args.batch_size,
        space=search_space,
        learner=args.learner,
        liar_strategy=args.liar_strategy,
        acq_func=args.acq_func,
        set_KAPPA=args.kappa,
        set_SEED=args.seed,
        set_NI=args.initial_points,
    )
    patch_skopt_categorical_imputer(ytoptimizer)

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tuner_dir = root / "tune_logs_two_stages_ytopt" / stamp
    tuner_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failures = []
    eval_idx = 0
    points = ytoptimizer.ask_initial(n_points=min(args.initial_points, args.max_evals))

    print(f"ytopt tuning logs: {tuner_dir}")
    print(f"Running up to {args.max_evals} benchmark evaluations.")

    while eval_idx < args.max_evals and points:
        tell_batch = []
        for point in points:
            if eval_idx >= args.max_evals:
                break
            eval_idx += 1
            normalized = normalize_point(point)
            print(
                f"\n[{eval_idx}/{args.max_evals}] "
                f"batch={normalized['batch']} s1_threads={normalized['stage1_threads']} "
                f"s2_threads={normalized['stage2_threads']} "
                f"s1_cb={normalized['stage1_callback_batch']} "
                f"s2_cb={normalized['stage2_callback_batch']} rate_hz={normalized['rate_hz']} "
                f"timeout_ms={normalized['timeout_ms']}",
                flush=True,
            )
            row, failure = run_benchmark(root, benchmark_script, tuner_dir, args, normalized, eval_idx)
            obj = objective_value(row, args.objective, args.failure_penalty)
            if failure is not None:
                forget_ytopt_point(ytoptimizer, point)
                failures.append(failure)
                print(f"  failed: {failure['error']}")
            else:
                tell_batch.append((point, obj))
                results.append(row)
                print(
                    f"  objective={obj:.6g} publisher_fps={fmt(row.get('publisher_avg_fps'))} "
                    f"stage1_fps={fmt(row.get('stage1_total_fps'))} "
                    f"stage2_fps={fmt(row.get('stage2_total_fps'))} "
                    f"pipeline_e2e_s={fmt(row.get('pipeline_e2e_s'))}"
                )

        remaining = args.max_evals - eval_idx
        if remaining <= 0:
            break

        if tell_batch:
            ytoptimizer.tell(tell_batch)

        next_count = min(args.batch_size, remaining)
        asked = list(ytoptimizer.ask(n_points=next_count))
        points = asked[0] if asked else []

    if results:
        reverse = args.objective in {"stage1_total_fps", "stage2_total_fps"}
        results.sort(key=lambda r: r[args.objective], reverse=reverse)
        aggregate_csv = tuner_dir / "aggregate.csv"
        write_csv(
            aggregate_csv,
            results,
            [
                "eval",
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
                "ytopt_eval_elapsed_s",
                "summary_path",
                "run_log",
            ],
        )
        print_results_table(results, args.objective, args.top_k)
        print(f"\nAggregate CSV written to: {aggregate_csv}")
    else:
        print("\nNo successful benchmark runs collected.")

    if failures:
        failures_csv = tuner_dir / "failures.csv"
        write_csv(
            failures_csv,
            failures,
            [
                "eval",
                "batch",
                "stage1_threads",
                "stage2_threads",
                "stage1_callback_batch",
                "stage2_callback_batch",
                "rate_hz",
                "timeout_ms",
                "elapsed_s",
                "log",
                "error",
            ],
        )
        print(f"Recorded {len(failures)} failures in: {failures_csv}")

    print(f"ytopt tuner logs written to: {tuner_dir}")

    if not results:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
