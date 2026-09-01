#!/usr/bin/env python3
"""
ytopt-libe hyperparameter tuner for the Drava PtychoNN two-stage pipeline.

Uses ytopt (ML-based Bayesian Optimization) with libEnsemble for parallel
evaluation of hyperparameter configurations.  The search space matches the
6D parameter space defined in agents/runner.py.

Requires the ytopt-libe stack (see requirements-ytopt.txt).

Usage
-----
Serial (1 generator + N-1 evaluators):
    python tune_ytopt.py --comms local --nworkers 4 --max-evals 30 --learner RF

MPI (1 manager + N-1 workers, 1 generator + N-2 evaluators):
    mpiexec -np 5 python tune_ytopt.py --max-evals 30 --learner RF

Options:
    --learner    Surrogate model: RF (Random Forest), GBRT, ET, DUMMY
    --max-evals  Total number of configurations to evaluate
    --nworkers   Number of workers (local comms only)
    --comms      Communication method: local or mpi (default: local)
    --num-frames Frames per benchmark run (default: 10000)
    --timeout-ms DRAVA_FETCH_TIMEOUT_MS (default: 200)
    --runs       Repetitions per configuration (default: 1)

References:
    https://github.com/ytopt-team/ytopt
    https://github.com/ytopt-team/ytopt/tree/main/ytopt-libe
"""

import csv
import datetime as dt
import os
import secrets
import sys
import time
from pathlib import Path

import multiprocessing
multiprocessing.set_start_method("fork", force=True)

import numpy as np

# ---------------------------------------------------------------------------
# libEnsemble imports
# ---------------------------------------------------------------------------
from libensemble.libE import libE
from libensemble.alloc_funcs.start_only_persistent import (
    only_persistent_gens as alloc_f,
)
from libensemble.tools import parse_args, add_unique_random_streams
from libensemble.message_numbers import (
    STOP_TAG,
    PERSIS_STOP,
    FINISHED_PERSISTENT_GEN_TAG,
    EVAL_GEN_TAG,
)
from libensemble.tools.persistent_support import PersistentSupport

# ---------------------------------------------------------------------------
# ytopt imports
# ---------------------------------------------------------------------------
import ConfigSpace as CS
import ConfigSpace.hyperparameters as CSH
from ytopt.search.optimizer import Optimizer

# ---------------------------------------------------------------------------
# Project-local imports
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "agents"))

from runner import RunConfig, run_benchmark  # noqa: E402

# ============================= Configuration ===============================

# Benchmark defaults (can be overridden via user_args)
DEFAULT_NUM_FRAMES = 10000
DEFAULT_TIMEOUT_MS = 200
DEFAULT_RUNS = 1


# ========================= Simulator Function ==============================

def sim_f(H, persis_info, sim_specs, libE_info):
    """
    libEnsemble simulator function.

    Receives a hyperparameter point from the generator, runs the Drava
    PtychoNN two-stage benchmark, and returns the pipeline end-to-end
    time as the objective (to be minimized).
    """
    t0 = time.time()

    # Extract hyperparameters from the libE history array
    batch_size = int(np.squeeze(H["batch_size"]))
    stage1_threads = int(np.squeeze(H["stage1_threads"]))
    stage2_threads = int(np.squeeze(H["stage2_threads"]))
    stage1_callback_batch = int(np.squeeze(H["stage1_callback_batch"]))
    stage2_callback_batch = int(np.squeeze(H["stage2_callback_batch"]))
    rate_hz = float(np.squeeze(H["rate_hz"]))

    config = RunConfig(
        batch_size=batch_size,
        stage1_threads=stage1_threads,
        stage2_threads=stage2_threads,
        stage1_callback_batch=stage1_callback_batch,
        stage2_callback_batch=stage2_callback_batch,
        rate_hz=rate_hz,
    )

    # Read benchmark settings from user dict
    user = sim_specs.get("user", {})
    num_frames = user.get("num_frames", DEFAULT_NUM_FRAMES)
    timeout_ms = user.get("timeout_ms", DEFAULT_TIMEOUT_MS)
    runs = user.get("runs", DEFAULT_RUNS)

    result = run_benchmark(
        config,
        num_frames=num_frames,
        timeout_ms=timeout_ms,
        runs=runs,
        cwd=SCRIPT_DIR,
    )

    # Objective: pipeline_e2e_s.  On failure, return a large penalty value.
    if result.success and result.pipeline_e2e_s is not None:
        objective = result.pipeline_e2e_s
    else:
        objective = 9999.0  # penalty for failed runs

    elapsed = time.time() - t0

    H_o = np.zeros(1, dtype=sim_specs["out"])
    H_o["objective"] = objective
    H_o["elapsed_sec"] = elapsed

    return H_o, persis_info


# ========================= Generator Function ==============================

def gen_f(H, persis_info, gen_specs, libE_info):
    """
    Persistent generator function wrapping the ytopt ask/tell interface.

    On the first call, asks for an initial batch of points.  On subsequent
    calls, tells the optimizer about completed evaluations and asks for
    new points.
    """
    ps = PersistentSupport(libE_info, EVAL_GEN_TAG)
    user_specs = gen_specs["user"]
    ytoptimizer = user_specs["ytoptimizer"]

    tag = None
    calc_in = None
    first_call = True
    first_write = True
    fields = [i[0] for i in gen_specs["out"]]

    # Send batches until manager sends stop tag
    while tag not in [STOP_TAG, PERSIS_STOP]:

        if first_call:
            ytopt_points = ytoptimizer.ask_initial(
                n_points=user_specs["num_sim_workers"]
            )
            batch_size = len(ytopt_points)
            first_call = False
        else:
            batch_size = len(calc_in)
            results = []
            for entry in calc_in:
                field_params = {}
                for field in fields:
                    field_params[field] = entry[field][0]
                results.append((field_params, entry["objective"]))
            ytoptimizer.tell(results)

            ytopt_points = ytoptimizer.ask(n_points=batch_size)
            ytopt_points = list(ytopt_points)[0]

        H_o = np.zeros(batch_size, dtype=gen_specs["out"])
        for i, entry in enumerate(ytopt_points):
            for key, value in entry.items():
                H_o[i][key] = value

        tag, Work, calc_in = ps.send_recv(H_o)

        # Append results to CSV as they arrive
        if calc_in is not None and len(calc_in):
            b = []
            for entry in calc_in[0]:
                try:
                    b.append(str(entry[0]))
                except (IndexError, TypeError):
                    b.append(str(entry))

            results_csv = os.path.join(
                user_specs.get("output_dir", "."), "results.csv"
            )
            with open(results_csv, "a") as f:
                if first_write:
                    f.write(",".join(calc_in.dtype.names) + "\n")
                    f.write(",".join(b) + "\n")
                    first_write = False
                else:
                    f.write(",".join(b) + "\n")

    return H_o, persis_info, FINISHED_PERSISTENT_GEN_TAG


# =============================== Main ======================================

def main():
    # Parse libEnsemble args: --comms, --nworkers, plus custom user args
    nworkers, is_manager, libE_specs, user_args_in = parse_args()
    num_sim_workers = nworkers - 1  # 1 worker reserved for the generator

    # Parse custom user arguments
    user_args = {}
    for entry in user_args_in:
        if entry.startswith("--"):
            if "=" in entry:
                key, value = entry.split("=", 1)
                key = key.strip("--")
            else:
                key = entry.strip("--")
                idx = user_args_in.index(entry)
                value = user_args_in[idx + 1] if idx + 1 < len(user_args_in) else ""
            user_args[key] = value

    # Validate required arguments
    required = ["learner", "max-evals"]
    for opt in required:
        if opt not in user_args:
            raise SystemExit(
                f"Missing required argument: --{opt}\n"
                f"Usage: python tune_ytopt.py --comms local --nworkers 4 "
                f"--max-evals 30 --learner RF"
            )

    num_frames = int(user_args.get("num-frames", DEFAULT_NUM_FRAMES))
    timeout_ms = int(user_args.get("timeout-ms", DEFAULT_TIMEOUT_MS))
    runs = int(user_args.get("runs", DEFAULT_RUNS))

    # Output directory
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = SCRIPT_DIR / "ytopt_results" / stamp
    if is_manager:
        output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # libEnsemble specs
    # -----------------------------------------------------------------------
    libE_specs["use_worker_dirs"] = True
    libE_specs["sim_dirs_make"] = False
    libE_specs["ensemble_dir_path"] = str(
        output_dir / ("ensemble_" + secrets.token_hex(nbytes=4))
    )

    # Parameter names (sorted lexicographically for ytopt compatibility)
    param_names = sorted([
        "batch_size",
        "rate_hz",
        "stage1_callback_batch",
        "stage1_threads",
        "stage2_callback_batch",
        "stage2_threads",
    ])

    # -----------------------------------------------------------------------
    # Simulator specs
    # -----------------------------------------------------------------------
    sim_specs = {
        "sim_f": sim_f,
        "in": param_names,
        "out": [("objective", float), ("elapsed_sec", float)],
        "user": {
            "num_frames": num_frames,
            "timeout_ms": timeout_ms,
            "runs": runs,
        },
    }

    # -----------------------------------------------------------------------
    # ConfigSpace: 6D hyperparameter search space
    # -----------------------------------------------------------------------
    cs = CS.ConfigurationSpace(seed=1234)

    # batch_size: categorical {64, 128, 256, 512, 1024}
    p_batch_size = CSH.CategoricalHyperparameter(
        name="batch_size", choices=[64, 128, 256, 512, 1024], default_value=256
    )
    # stage1_threads: integer [1, 32]
    p_stage1_threads = CSH.UniformIntegerHyperparameter(
        name="stage1_threads", lower=1, upper=32, default_value=4
    )
    # stage2_threads: integer [1, 16]
    p_stage2_threads = CSH.UniformIntegerHyperparameter(
        name="stage2_threads", lower=1, upper=16, default_value=4
    )
    # stage1_callback_batch: categorical {32, 64, 128, 256, 512, 1024}
    p_stage1_cb = CSH.CategoricalHyperparameter(
        name="stage1_callback_batch",
        choices=[32, 64, 128, 256, 512, 1024],
        default_value=256,
    )
    # stage2_callback_batch: categorical {16, 32, 64, 128, 256, 512}
    p_stage2_cb = CSH.CategoricalHyperparameter(
        name="stage2_callback_batch",
        choices=[16, 32, 64, 128, 256, 512],
        default_value=64,
    )
    # rate_hz: float [0.0, 50000.0]  (0 = max speed, no pacing)
    p_rate_hz = CSH.UniformFloatHyperparameter(
        name="rate_hz", lower=0.0, upper=50000.0, default_value=0.0
    )

    cs.add_hyperparameters([
        p_batch_size,
        p_stage1_threads,
        p_stage2_threads,
        p_stage1_cb,
        p_stage2_cb,
        p_rate_hz,
    ])

    # -----------------------------------------------------------------------
    # ytopt Optimizer
    # -----------------------------------------------------------------------
    ytoptimizer = Optimizer(
        num_workers=num_sim_workers,
        space=cs,
        learner=user_args["learner"],
        liar_strategy="cl_max",
        acq_func="gp_hedge",
        set_KAPPA=1.96,
        set_SEED=2345,
        set_NI=10,
    )

    # -----------------------------------------------------------------------
    # Generator specs
    # -----------------------------------------------------------------------
    # Build gen_specs 'out' dtype list from ConfigSpace.
    # Integers -> int, floats -> float, categoricals -> int (all our
    # categoricals have integer choices).
    gen_out = []
    for name in param_names:
        hp = cs.get_hyperparameter(name)
        if isinstance(hp, CSH.UniformFloatHyperparameter):
            gen_out.append((name, float, (1,)))
        elif isinstance(hp, CSH.UniformIntegerHyperparameter):
            gen_out.append((name, int, (1,)))
        elif isinstance(hp, CSH.CategoricalHyperparameter):
            # All our categorical choices are integers
            gen_out.append((name, int, (1,)))
        else:
            gen_out.append((name, "<U24", (1,)))

    gen_specs = {
        "gen_f": gen_f,
        "out": gen_out,
        "persis_in": param_names + ["objective", "elapsed_sec"],
        "user": {
            "ytoptimizer": ytoptimizer,
            "num_sim_workers": num_sim_workers,
            "output_dir": str(output_dir),
        },
    }

    # -----------------------------------------------------------------------
    # Allocation and exit criteria
    # -----------------------------------------------------------------------
    alloc_specs = {
        "alloc_f": alloc_f,
        "user": {"async_return": True},
    }

    exit_criteria = {"gen_max": int(user_args["max-evals"])}

    persis_info = add_unique_random_streams({}, nworkers + 1)

    # -----------------------------------------------------------------------
    # Run libEnsemble
    # -----------------------------------------------------------------------
    if is_manager:
        print(f"ytopt-libe PtychoNN tuner")
        print(f"  Learner:      {user_args['learner']}")
        print(f"  Max evals:    {user_args['max-evals']}")
        print(f"  Sim workers:  {num_sim_workers}")
        print(f"  Num frames:   {num_frames}")
        print(f"  Timeout ms:   {timeout_ms}")
        print(f"  Output dir:   {output_dir}")
        print()

    H, persis_info, flag = libE(
        sim_specs,
        gen_specs,
        exit_criteria,
        persis_info,
        alloc_specs=alloc_specs,
        libE_specs=libE_specs,
    )

    # -----------------------------------------------------------------------
    # Post-processing (manager only)
    # -----------------------------------------------------------------------
    if is_manager:
        print("\nlibEnsemble has completed evaluations.")

        # Extract completed evaluations and sort by objective
        completed = H[H["sim_ended"]]
        if len(completed) > 0:
            # Sort by objective (ascending = best first for minimization)
            sort_idx = np.argsort(completed["objective"])
            completed = completed[sort_idx]

            # Write aggregate CSV
            agg_csv = output_dir / "aggregate.csv"
            fieldnames = param_names + ["objective", "elapsed_sec"]
            with open(agg_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)
                for row in completed:
                    values = []
                    for name in param_names:
                        val = row[name]
                        if hasattr(val, "__len__") and len(val) == 1:
                            val = val[0]
                        values.append(val)
                    values.append(row["objective"])
                    values.append(row["elapsed_sec"])
                    writer.writerow(values)

            print(f"\nAggregate CSV: {agg_csv}")
            print(f"Results CSV:   {output_dir / 'results.csv'}")

            # Print top-5 results
            print("\nTop-5 configurations (by pipeline_e2e_s):")
            print(
                f"{'Rank':>4}  {'Batch':>5}  {'S1 Thr':>6}  {'S2 Thr':>6}  "
                f"{'S1 CB':>5}  {'S2 CB':>5}  {'Rate Hz':>8}  {'E2E (s)':>8}"
            )
            print("-" * 70)
            for rank, row in enumerate(completed[:5], start=1):
                def _val(name):
                    v = row[name]
                    if hasattr(v, "__len__") and len(v) == 1:
                        return v[0]
                    return v

                print(
                    f"{rank:>4}  {int(_val('batch_size')):>5}  "
                    f"{int(_val('stage1_threads')):>6}  "
                    f"{int(_val('stage2_threads')):>6}  "
                    f"{int(_val('stage1_callback_batch')):>5}  "
                    f"{int(_val('stage2_callback_batch')):>5}  "
                    f"{float(_val('rate_hz')):>8.1f}  "
                    f"{float(row['objective']):>8.3f}"
                )
        else:
            print("No completed evaluations found.")

        print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()

