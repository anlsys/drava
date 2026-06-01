#!/usr/bin/env python3
"""
Agent 1: Guided Exploration for Drava Pipeline Hyperparameter Optimization.

Uses Optuna's Tree-structured Parzen Estimator (TPE) sampler for Bayesian
optimization over the Drava two-stage PtychoNN pipeline configuration space.
This replaces the brute-force grid search in tune_two_stage.py with an
intelligent sampling strategy that:

  1. Explores the hyperparameter space efficiently using a probabilistic model.
  2. Balances exploration vs. exploitation via TPE's acquisition function.
  3. Supports pruning of unpromising trials based on intermediate results.
  4. Persists study state in an SQLite database for resumability.
  5. Produces Optuna's built-in visualization (parameter importance, Pareto
     front, optimization history, etc.).

Hyperparameter space (6 dimensions):
  - batch_size:             {64, 128, 256, 512, 1024}  (categorical)
  - stage1_threads:         [1, 32]                    (integer)
  - stage2_threads:         [1, 16]                    (integer)
  - stage1_callback_batch:  {32, 64, 128, 256, 512, 1024} (categorical)
  - stage2_callback_batch:  {16, 32, 64, 128, 256, 512}   (categorical)
  - rate_hz:                [0, 50000]                 (float, 0 = max speed)

Objective:
  - Primary: minimize pipeline_e2e_s (end-to-end latency)
  - Can also target: maximize stage1_total_fps, maximize stage2_total_fps

Usage:
  python -m agents.agent_guided_exploration --n-trials 50 --objective pipeline_e2e_s

  # Resume a previous study:
  python -m agents.agent_guided_exploration --study-name my_study --storage sqlite:///my_study.db

  # Multi-objective (Pareto front):
  python -m agents.agent_guided_exploration --multi-objective --n-trials 100
"""

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Optional

import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

from runner import RunConfig, RunResult, run_benchmark, fmt, PARAM_SPACE, OBJECTIVES


def parse_args():
    p = argparse.ArgumentParser(
        description="Agent 1: Guided exploration via Optuna TPE for Drava pipeline tuning."
    )
    # Optuna study settings
    p.add_argument("--study-name", default=None,
                   help="Optuna study name. Defaults to timestamped name.")
    p.add_argument("--storage", default=None,
                   help="Optuna storage URL (e.g., sqlite:///study.db). "
                        "Default: in-memory (no persistence).")
    p.add_argument("--n-trials", type=int, default=50,
                   help="Number of trials to run.")
    p.add_argument("--timeout", type=float, default=None,
                   help="Stop study after this many seconds.")
    p.add_argument("--objective", default="pipeline_e2e_s",
                   choices=list(OBJECTIVES.keys()),
                   help="Single-objective metric to optimize.")
    p.add_argument("--multi-objective", action="store_true",
                   help="Run multi-objective optimization (minimize pipeline_e2e_s, "
                        "maximize stage1_total_fps, maximize stage2_total_fps).")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for TPE sampler.")

    # Search space overrides (narrow the default ranges)
    p.add_argument("--batch-sizes", default=None,
                   help="Comma-separated batch sizes to consider (overrides default).")
    p.add_argument("--s1-threads-range", default=None,
                   help="Stage1 threads range as 'low,high' (overrides default 1,32).")
    p.add_argument("--s2-threads-range", default=None,
                   help="Stage2 threads range as 'low,high' (overrides default 1,16).")
    p.add_argument("--s1-cb-choices", default=None,
                   help="Comma-separated stage1 callback batch choices.")
    p.add_argument("--s2-cb-choices", default=None,
                   help="Comma-separated stage2 callback batch choices.")
    p.add_argument("--rate-hz-range", default=None,
                   help="Rate Hz range as 'low,high' (overrides default 0,50000).")
    p.add_argument("--fixed-rate-hz", type=float, default=None,
                   help="Fix rate_hz to this value (remove from search space).")

    # Benchmark execution
    p.add_argument("--python", default=sys.executable,
                   help="Python executable for benchmark subprocess.")
    p.add_argument("--num-frames", type=int, default=10000,
                   help="Frame count per benchmark run.")
    p.add_argument("--timeout-ms", type=int, default=200,
                   help="DRAVA_FETCH_TIMEOUT_MS per run.")
    p.add_argument("--runs-per-trial", type=int, default=1,
                   help="Repeated runs per trial (averaged).")
    p.add_argument("--extra-args", default="",
                   help="Extra args passed to benchmark_two_stages.py.")
    p.add_argument("--keep-going", action="store_true",
                   help="Report failed trials as pruned instead of raising.")

    # Output
    p.add_argument("--out-dir", default=None,
                   help="Output directory for results. Default: auto-generated.")
    p.add_argument("--export-csv", action="store_true",
                   help="Export all trials to CSV at the end.")
    p.add_argument("--visualize", action="store_true",
                   help="Generate Optuna visualization plots.")
    return p.parse_args()


def _parse_int_list(raw: str) -> list:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _parse_float_pair(raw: str) -> tuple:
    parts = [float(x.strip()) for x in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Expected 'low,high', got: {raw}")
    return parts[0], parts[1]


def _parse_int_pair(raw: str) -> tuple:
    parts = [int(x.strip()) for x in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Expected 'low,high', got: {raw}")
    return parts[0], parts[1]


class GuidedExplorationAgent:
    """
    Optuna-based guided exploration agent.

    Builds an Optuna study with TPE sampling, defines the hyperparameter search
    space, and evaluates each trial by running the two-stage benchmark.
    """

    def __init__(self, args):
        self.args = args
        self.ptychonn_dir = Path(__file__).resolve().parent.parent
        self.stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.out_dir:
            self.out_dir = Path(args.out_dir)
        else:
            self.out_dir = self.ptychonn_dir / "agent_exploration_logs" / self.stamp
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # Parse search space overrides
        self.batch_choices = (
            _parse_int_list(args.batch_sizes) if args.batch_sizes
            else PARAM_SPACE["batch_size"]["choices"]
        )
        self.s1_threads_range = (
            _parse_int_pair(args.s1_threads_range) if args.s1_threads_range
            else (PARAM_SPACE["stage1_threads"]["low"],
                  PARAM_SPACE["stage1_threads"]["high"])
        )
        self.s2_threads_range = (
            _parse_int_pair(args.s2_threads_range) if args.s2_threads_range
            else (PARAM_SPACE["stage2_threads"]["low"],
                  PARAM_SPACE["stage2_threads"]["high"])
        )
        self.s1_cb_choices = (
            _parse_int_list(args.s1_cb_choices) if args.s1_cb_choices
            else PARAM_SPACE["stage1_callback_batch"]["choices"]
        )
        self.s2_cb_choices = (
            _parse_int_list(args.s2_cb_choices) if args.s2_cb_choices
            else PARAM_SPACE["stage2_callback_batch"]["choices"]
        )
        self.rate_hz_range = (
            _parse_float_pair(args.rate_hz_range) if args.rate_hz_range
            else (PARAM_SPACE["rate_hz"]["low"],
                  PARAM_SPACE["rate_hz"]["high"])
        )

        self.extra_args = [x for x in args.extra_args.split() if x.strip()]

    def _suggest_config(self, trial: optuna.Trial) -> RunConfig:
        """Sample a hyperparameter configuration from the Optuna trial."""
        batch_size = trial.suggest_categorical(
            "batch_size", self.batch_choices
        )
        stage1_threads = trial.suggest_int(
            "stage1_threads", *self.s1_threads_range
        )
        stage2_threads = trial.suggest_int(
            "stage2_threads", *self.s2_threads_range
        )
        stage1_callback_batch = trial.suggest_categorical(
            "stage1_callback_batch", self.s1_cb_choices
        )
        stage2_callback_batch = trial.suggest_categorical(
            "stage2_callback_batch", self.s2_cb_choices
        )

        if self.args.fixed_rate_hz is not None:
            rate_hz = self.args.fixed_rate_hz
        else:
            rate_hz = trial.suggest_float(
                "rate_hz", *self.rate_hz_range
            )

        return RunConfig(
            batch_size=batch_size,
            stage1_threads=stage1_threads,
            stage2_threads=stage2_threads,
            stage1_callback_batch=stage1_callback_batch,
            stage2_callback_batch=stage2_callback_batch,
            rate_hz=rate_hz,
        )

    def _evaluate(self, config: RunConfig) -> RunResult:
        """Run the benchmark with the given config."""
        return run_benchmark(
            config,
            python=self.args.python,
            num_frames=self.args.num_frames,
            timeout_ms=self.args.timeout_ms,
            runs=self.args.runs_per_trial,
            extra_args=self.extra_args if self.extra_args else None,
            cwd=self.ptychonn_dir,
        )

    def single_objective(self, trial: optuna.Trial) -> float:
        """Optuna objective function for single-objective optimization."""
        config = self._suggest_config(trial)
        trial.set_user_attr("config_label", config.as_label())

        result = self._evaluate(config)

        # Store all metrics as user attributes for later analysis
        for key, val in result.metrics_dict().items():
            trial.set_user_attr(key, val)

        if not result.success:
            trial.set_user_attr("error", result.error or "unknown")
            if self.args.keep_going:
                raise optuna.TrialPruned(f"Benchmark failed: {result.error}")
            raise RuntimeError(f"Benchmark failed: {result.error}")

        obj_val = result.objective_value(self.args.objective)
        if obj_val is None:
            raise optuna.TrialPruned(f"Objective {self.args.objective} is None")

        print(
            f"  Trial {trial.number}: {config.as_label()} -> "
            f"{self.args.objective}={fmt(obj_val)}"
        )
        return obj_val

    def multi_objective(self, trial: optuna.Trial) -> tuple:
        """
        Optuna objective function for multi-objective optimization.

        Returns (pipeline_e2e_s, -stage1_total_fps, -stage2_total_fps).
        All are minimized, so we negate FPS values.
        """
        config = self._suggest_config(trial)
        trial.set_user_attr("config_label", config.as_label())

        result = self._evaluate(config)

        for key, val in result.metrics_dict().items():
            trial.set_user_attr(key, val)

        if not result.success:
            trial.set_user_attr("error", result.error or "unknown")
            if self.args.keep_going:
                raise optuna.TrialPruned(f"Benchmark failed: {result.error}")
            raise RuntimeError(f"Benchmark failed: {result.error}")

        e2e = result.pipeline_e2e_s
        s1_fps = result.stage1_total_fps
        s2_fps = result.stage2_total_fps

        if any(v is None for v in [e2e, s1_fps, s2_fps]):
            raise optuna.TrialPruned("One or more objectives are None")

        return (e2e, -s1_fps, -s2_fps)

    def create_study(self) -> optuna.Study:
        """Create or load an Optuna study."""
        study_name = self.args.study_name or f"drava_exploration_{self.stamp}"

        sampler = TPESampler(
            seed=self.args.seed,
            n_startup_trials=10,  # Random exploration before TPE kicks in
            multivariate=True,    # Model parameter correlations
        )

        if self.args.multi_objective:
            study = optuna.create_study(
                study_name=study_name,
                storage=self.args.storage,
                directions=["minimize", "minimize", "minimize"],
                sampler=sampler,
                load_if_exists=True,
            )
        else:
            direction = OBJECTIVES[self.args.objective]
            study = optuna.create_study(
                study_name=study_name,
                storage=self.args.storage,
                direction=direction,
                sampler=sampler,
                pruner=MedianPruner(n_startup_trials=5),
                load_if_exists=True,
            )

        return study

    def run(self):
        """Execute the guided exploration."""
        study = self.create_study()

        print(f"Study: {study.study_name}")
        print(f"Objective: {self.args.objective} ({OBJECTIVES[self.args.objective]})")
        print(f"Trials: {self.args.n_trials}")
        print(f"Output: {self.out_dir}")
        print(f"Search space:")
        print(f"  batch_size:            {self.batch_choices}")
        print(f"  stage1_threads:        [{self.s1_threads_range[0]}, {self.s1_threads_range[1]}]")
        print(f"  stage2_threads:        [{self.s2_threads_range[0]}, {self.s2_threads_range[1]}]")
        print(f"  stage1_callback_batch: {self.s1_cb_choices}")
        print(f"  stage2_callback_batch: {self.s2_cb_choices}")
        if self.args.fixed_rate_hz is not None:
            print(f"  rate_hz:               {self.args.fixed_rate_hz} (fixed)")
        else:
            print(f"  rate_hz:               [{self.rate_hz_range[0]}, {self.rate_hz_range[1]}]")
        print()

        # Save search config for reproducibility
        search_config = {
            "study_name": study.study_name,
            "objective": self.args.objective,
            "multi_objective": self.args.multi_objective,
            "n_trials": self.args.n_trials,
            "seed": self.args.seed,
            "num_frames": self.args.num_frames,
            "timeout_ms": self.args.timeout_ms,
            "batch_choices": self.batch_choices,
            "s1_threads_range": list(self.s1_threads_range),
            "s2_threads_range": list(self.s2_threads_range),
            "s1_cb_choices": self.s1_cb_choices,
            "s2_cb_choices": self.s2_cb_choices,
            "rate_hz_range": list(self.rate_hz_range),
            "fixed_rate_hz": self.args.fixed_rate_hz,
        }
        config_path = self.out_dir / "search_config.json"
        with open(config_path, "w") as f:
            json.dump(search_config, f, indent=2)

        # Run optimization
        objective_fn = (
            self.multi_objective if self.args.multi_objective
            else self.single_objective
        )
        study.optimize(
            objective_fn,
            n_trials=self.args.n_trials,
            timeout=self.args.timeout,
            catch=(RuntimeError,) if self.args.keep_going else (),
        )

        # Report results
        self._report_results(study)

        if self.args.export_csv:
            self._export_csv(study)

        if self.args.visualize:
            self._generate_visualizations(study)

        return study

    def _report_results(self, study: optuna.Study):
        """Print summary of best trials."""
        print("\n" + "=" * 80)
        print("EXPLORATION RESULTS")
        print("=" * 80)

        completed = [t for t in study.trials
                     if t.state == optuna.trial.TrialState.COMPLETE]
        pruned = [t for t in study.trials
                  if t.state == optuna.trial.TrialState.PRUNED]
        failed = [t for t in study.trials
                  if t.state == optuna.trial.TrialState.FAIL]

        print(f"\nTrials: {len(study.trials)} total, "
              f"{len(completed)} completed, "
              f"{len(pruned)} pruned, "
              f"{len(failed)} failed")

        if self.args.multi_objective:
            best_trials = study.best_trials
            print(f"\nPareto front: {len(best_trials)} trials")
            print(
                "\n| # | Pipeline E2E (s) | Stage1 FPS | Stage2 FPS | Config |"
            )
            print("|---:|---:|---:|---:|---|")
            for i, trial in enumerate(best_trials, 1):
                e2e = trial.values[0]
                s1_fps = -trial.values[1]  # un-negate
                s2_fps = -trial.values[2]
                label = trial.user_attrs.get("config_label", "?")
                print(f"| {i} | {fmt(e2e)} | {fmt(s1_fps)} | {fmt(s2_fps)} | {label} |")
        else:
            best = study.best_trial
            print(f"\nBest trial: #{best.number}")
            print(f"  {self.args.objective} = {fmt(best.value)}")
            print(f"  Config: {best.user_attrs.get('config_label', '?')}")
            print(f"  Parameters: {best.params}")

            # Top 10
            sorted_trials = sorted(
                completed,
                key=lambda t: t.value,
                reverse=(OBJECTIVES[self.args.objective] == "maximize"),
            )
            print(
                f"\nTop 10 (by {self.args.objective}):"
            )
            print(
                "\n| Rank | Trial | Pipeline E2E | Stage1 FPS | Stage2 FPS | Config |"
            )
            print("|---:|---:|---:|---:|---:|---|")
            for rank, trial in enumerate(sorted_trials[:10], 1):
                e2e = trial.user_attrs.get("pipeline_e2e_s")
                s1 = trial.user_attrs.get("stage1_total_fps")
                s2 = trial.user_attrs.get("stage2_total_fps")
                label = trial.user_attrs.get("config_label", "?")
                print(
                    f"| {rank} | {trial.number} | {fmt(e2e)} | {fmt(s1)} | {fmt(s2)} | {label} |"
                )

        # Parameter importance (single-objective only)
        if not self.args.multi_objective and len(completed) >= 5:
            try:
                importance = optuna.importance.get_param_importances(study)
                print("\nParameter importance:")
                for param, imp in importance.items():
                    bar = "#" * int(imp * 40)
                    print(f"  {param:30s} {imp:.4f} {bar}")
            except Exception as exc:
                print(f"\nParameter importance computation failed: {exc}")

    def _export_csv(self, study: optuna.Study):
        """Export all trials to CSV."""
        csv_path = self.out_dir / "trials.csv"
        trials = study.trials

        if not trials:
            print("No trials to export.")
            return

        # Collect all parameter and attribute keys
        param_keys = set()
        attr_keys = set()
        for t in trials:
            param_keys.update(t.params.keys())
            attr_keys.update(t.user_attrs.keys())
        param_keys = sorted(param_keys)
        attr_keys = sorted(attr_keys)

        fieldnames = (
            ["trial", "state", "value"]
            + [f"param_{k}" for k in param_keys]
            + [f"attr_{k}" for k in attr_keys]
        )

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in trials:
                row = {
                    "trial": t.number,
                    "state": t.state.name,
                    "value": t.value if t.value is not None else "",
                }
                for k in param_keys:
                    row[f"param_{k}"] = t.params.get(k, "")
                for k in attr_keys:
                    row[f"attr_{k}"] = t.user_attrs.get(k, "")
                writer.writerow(row)

        print(f"\nTrials exported to: {csv_path}")

    def _generate_visualizations(self, study: optuna.Study):
        """Generate Optuna visualization plots."""
        completed = [t for t in study.trials
                     if t.state == optuna.trial.TrialState.COMPLETE]
        if len(completed) < 3:
            print("\nToo few completed trials for visualization.")
            return

        try:
            from optuna.visualization import (
                plot_optimization_history,
                plot_param_importances,
                plot_parallel_coordinate,
                plot_slice,
                plot_contour,
            )
        except ImportError:
            print("\nOptuna visualization requires plotly. Install: pip install plotly")
            return

        viz_dir = self.out_dir / "plots"
        viz_dir.mkdir(exist_ok=True)
        generated = []

        try:
            fig = plot_optimization_history(study)
            path = viz_dir / "optimization_history.html"
            fig.write_html(str(path))
            generated.append(path)
        except Exception as exc:
            print(f"  optimization_history failed: {exc}")

        if not self.args.multi_objective and len(completed) >= 5:
            try:
                fig = plot_param_importances(study)
                path = viz_dir / "param_importances.html"
                fig.write_html(str(path))
                generated.append(path)
            except Exception as exc:
                print(f"  param_importances failed: {exc}")

        try:
            fig = plot_parallel_coordinate(study)
            path = viz_dir / "parallel_coordinate.html"
            fig.write_html(str(path))
            generated.append(path)
        except Exception as exc:
            print(f"  parallel_coordinate failed: {exc}")

        try:
            fig = plot_slice(study)
            path = viz_dir / "slice_plot.html"
            fig.write_html(str(path))
            generated.append(path)
        except Exception as exc:
            print(f"  slice_plot failed: {exc}")

        if len(completed) >= 5:
            try:
                fig = plot_contour(study)
                path = viz_dir / "contour_plot.html"
                fig.write_html(str(path))
                generated.append(path)
            except Exception as exc:
                print(f"  contour_plot failed: {exc}")

        if self.args.multi_objective:
            try:
                from optuna.visualization import plot_pareto_front
                fig = plot_pareto_front(study)
                path = viz_dir / "pareto_front.html"
                fig.write_html(str(path))
                generated.append(path)
            except Exception as exc:
                print(f"  pareto_front failed: {exc}")

        if generated:
            print(f"\nVisualization plots ({len(generated)}):")
            for p in generated:
                print(f"  {p}")


def main():
    args = parse_args()
    agent = GuidedExplorationAgent(args)
    agent.run()


if __name__ == "__main__":
    main()
