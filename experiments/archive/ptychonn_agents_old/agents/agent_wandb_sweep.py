#!/usr/bin/env python3
"""
Agent 2: Weights & Biases Sweep for Drava Pipeline Trend Analysis.

Uses W&B Sweeps to explore the hyperparameter space and discover trends
across the Drava two-stage PtychoNN pipeline configuration. Unlike Agent 1
(Optuna-based guided exploration), this agent focuses on:

  1. Logging all experiment metadata and metrics to W&B for rich visualization.
  2. Using W&B's built-in sweep strategies (Bayesian, random, grid) with
     automatic early termination via Hyperband.
  3. Enabling trend discovery through W&B's parallel coordinates, parameter
     importance, and correlation plots in the dashboard.
  4. Supporting team collaboration: results are visible in the W&B web UI.

The agent can operate in two modes:
  (a) **Sweep mode** (default): Creates a W&B sweep and runs the agent as a
      sweep worker, letting W&B's controller suggest configurations.
  (b) **Manual mode** (--manual): Runs a standalone loop with its own sampling
      logic but logs everything to W&B for post-hoc analysis.

Trend analysis workflow:
  - After the sweep completes, open the W&B dashboard to:
    - View parallel coordinates plot: reveals which parameter combinations
      correlate with best performance.
    - View parameter importance: which hyperparameters matter most.
    - View scatter/line plots: metric vs. each parameter.
    - Compare runs side-by-side for detailed analysis.

Usage:
  # Create and run a W&B sweep (Bayesian strategy):
  python -m agents.agent_wandb_sweep --method bayes --count 50

  # Grid sweep:
  python -m agents.agent_wandb_sweep --method grid

  # Random search:
  python -m agents.agent_wandb_sweep --method random --count 30

  # Manual mode (log to W&B without using sweep controller):
  python -m agents.agent_wandb_sweep --manual --count 20

  # Join an existing sweep:
  python -m agents.agent_wandb_sweep --sweep-id <SWEEP_ID>

Prerequisites:
  pip install wandb
  wandb login  # authenticate with your W&B account
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Optional

import wandb

from runner import RunConfig, RunResult, run_benchmark, fmt, PARAM_SPACE, OBJECTIVES


def parse_args():
    p = argparse.ArgumentParser(
        description="Agent 2: W&B Sweep for Drava pipeline trend analysis."
    )
    # W&B project settings
    p.add_argument("--project", default="drava-ptychonn-tuning",
                   help="W&B project name.")
    p.add_argument("--entity", default=None,
                   help="W&B entity (team/user). Default: your default entity.")
    p.add_argument("--sweep-id", default=None,
                   help="Existing W&B sweep ID to join. Creates new sweep if not set.")
    p.add_argument("--tags", default="",
                   help="Comma-separated tags for W&B runs.")

    # Sweep strategy
    p.add_argument("--method", default="bayes",
                   choices=["bayes", "random", "grid"],
                   help="W&B sweep search method.")
    p.add_argument("--count", type=int, default=50,
                   help="Number of sweep runs.")
    p.add_argument("--metric", default="pipeline_e2e_s",
                   choices=list(OBJECTIVES.keys()),
                   help="Primary metric to optimize.")
    p.add_argument("--early-terminate", action="store_true",
                   help="Enable Hyperband early termination.")

    # Manual mode
    p.add_argument("--manual", action="store_true",
                   help="Manual mode: run own loop, log to W&B (no sweep controller).")

    # Search space overrides
    p.add_argument("--batch-sizes", default=None,
                   help="Comma-separated batch sizes (overrides default).")
    p.add_argument("--s1-threads-range", default=None,
                   help="Stage1 threads as 'min,max'.")
    p.add_argument("--s2-threads-range", default=None,
                   help="Stage2 threads as 'min,max'.")
    p.add_argument("--s1-cb-choices", default=None,
                   help="Comma-separated stage1 callback batch choices.")
    p.add_argument("--s2-cb-choices", default=None,
                   help="Comma-separated stage2 callback batch choices.")
    p.add_argument("--fixed-rate-hz", type=float, default=None,
                   help="Fix rate_hz (remove from search space).")

    # Benchmark execution
    p.add_argument("--python", default=sys.executable,
                   help="Python executable.")
    p.add_argument("--num-frames", type=int, default=10000,
                   help="Frame count per run.")
    p.add_argument("--timeout-ms", type=int, default=200,
                   help="DRAVA_FETCH_TIMEOUT_MS.")
    p.add_argument("--runs-per-config", type=int, default=1,
                   help="Repeated runs per config (averaged).")
    p.add_argument("--extra-args", default="",
                   help="Extra args for benchmark_two_stages.py.")
    p.add_argument("--keep-going", action="store_true",
                   help="Continue after failed runs.")

    # Output
    p.add_argument("--out-dir", default=None,
                   help="Local output directory. Default: auto-generated.")
    return p.parse_args()


def _parse_int_list(raw: str) -> list:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _parse_int_pair(raw: str) -> tuple:
    parts = [int(x.strip()) for x in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"Expected 'min,max', got: {raw}")
    return parts[0], parts[1]


class WandBSweepAgent:
    """
    W&B-based sweep agent for trend analysis over Drava pipeline configurations.

    Creates a W&B sweep configuration, registers an agent function that evaluates
    each suggested configuration by running the two-stage benchmark, and logs
    all metrics to W&B for visualization and trend discovery.
    """

    def __init__(self, args):
        self.args = args
        self.ptychonn_dir = Path(__file__).resolve().parent.parent
        self.stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.out_dir:
            self.out_dir = Path(args.out_dir)
        else:
            self.out_dir = self.ptychonn_dir / "agent_wandb_logs" / self.stamp
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.extra_args = [x for x in args.extra_args.split() if x.strip()]
        self.tags = [t.strip() for t in args.tags.split(",") if t.strip()]

        # Parse search space
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

    def _build_sweep_config(self) -> dict:
        """
        Build the W&B sweep configuration dictionary.

        Defines the parameter space, optimization metric, search method,
        and optional early termination.
        """
        goal = "minimize" if OBJECTIVES[self.args.metric] == "minimize" else "maximize"

        parameters = {
            "batch_size": {"values": self.batch_choices},
            "stage1_threads": {
                "min": self.s1_threads_range[0],
                "max": self.s1_threads_range[1],
                "distribution": "int_uniform",
            },
            "stage2_threads": {
                "min": self.s2_threads_range[0],
                "max": self.s2_threads_range[1],
                "distribution": "int_uniform",
            },
            "stage1_callback_batch": {"values": self.s1_cb_choices},
            "stage2_callback_batch": {"values": self.s2_cb_choices},
        }

        if self.args.fixed_rate_hz is not None:
            parameters["rate_hz"] = {"value": self.args.fixed_rate_hz}
        else:
            parameters["rate_hz"] = {
                "min": 0.0,
                "max": 50000.0,
                "distribution": "uniform",
            }

        sweep_config = {
            "name": f"drava-ptychonn-{self.stamp}",
            "method": self.args.method,
            "metric": {
                "name": self.args.metric,
                "goal": goal,
            },
            "parameters": parameters,
        }

        if self.args.early_terminate:
            sweep_config["early_terminate"] = {
                "type": "hyperband",
                "min_iter": 3,
                "max_iter": 27,
                "s": 2,
            }

        return sweep_config

    def _evaluate_config(self, config: RunConfig) -> RunResult:
        """Run the benchmark with the given configuration."""
        return run_benchmark(
            config,
            python=self.args.python,
            num_frames=self.args.num_frames,
            timeout_ms=self.args.timeout_ms,
            runs=self.args.runs_per_config,
            extra_args=self.extra_args if self.extra_args else None,
            cwd=self.ptychonn_dir,
        )

    def _sweep_train_fn(self):
        """
        W&B sweep agent function.

        Called by wandb.agent() for each trial. Reads the suggested
        hyperparameters from wandb.config, runs the benchmark, and logs
        all metrics.
        """
        run = wandb.init(tags=self.tags)

        try:
            # Read hyperparameters from W&B sweep controller
            config = RunConfig(
                batch_size=wandb.config.batch_size,
                stage1_threads=wandb.config.stage1_threads,
                stage2_threads=wandb.config.stage2_threads,
                stage1_callback_batch=wandb.config.stage1_callback_batch,
                stage2_callback_batch=wandb.config.stage2_callback_batch,
                rate_hz=wandb.config.rate_hz,
            )

            print(f"\n[W&B Run {run.name}] Config: {config.as_label()}")

            result = self._evaluate_config(config)

            if result.success:
                # Log all metrics
                metrics = result.metrics_dict()
                metrics["success"] = 1
                wandb.log(metrics)

                # Log summary metrics for sweep comparison
                for key, val in metrics.items():
                    wandb.summary[key] = val
                wandb.summary["config_label"] = config.as_label()

                print(
                    f"  Result: {self.args.metric}={fmt(result.objective_value(self.args.metric))}"
                )
            else:
                wandb.log({"success": 0})
                wandb.summary["error"] = result.error or "unknown"
                wandb.summary["config_label"] = config.as_label()
                print(f"  FAILED: {result.error}")

                if not self.args.keep_going:
                    raise RuntimeError(f"Benchmark failed: {result.error}")

        finally:
            wandb.finish()

    def _manual_run(self):
        """
        Manual mode: run a standalone loop logging to W&B.

        Uses Python's random module to sample configurations, evaluates them,
        and logs everything to W&B. Useful when the sweep controller is not
        desired but W&B's visualization is still wanted.
        """
        import random

        print(f"Manual mode: running {self.args.count} configurations")
        print(f"Project: {self.args.project}")

        for i in range(self.args.count):
            config = RunConfig(
                batch_size=random.choice(self.batch_choices),
                stage1_threads=random.randint(*self.s1_threads_range),
                stage2_threads=random.randint(*self.s2_threads_range),
                stage1_callback_batch=random.choice(self.s1_cb_choices),
                stage2_callback_batch=random.choice(self.s2_cb_choices),
                rate_hz=(
                    self.args.fixed_rate_hz if self.args.fixed_rate_hz is not None
                    else random.uniform(0.0, 50000.0)
                ),
            )

            run = wandb.init(
                project=self.args.project,
                entity=self.args.entity,
                name=f"manual_{i:03d}_{config.as_label()}",
                config={
                    "batch_size": config.batch_size,
                    "stage1_threads": config.stage1_threads,
                    "stage2_threads": config.stage2_threads,
                    "stage1_callback_batch": config.stage1_callback_batch,
                    "stage2_callback_batch": config.stage2_callback_batch,
                    "rate_hz": config.rate_hz,
                    "num_frames": self.args.num_frames,
                    "timeout_ms": self.args.timeout_ms,
                },
                tags=self.tags + ["manual"],
                reinit=True,
            )

            print(f"\n[{i + 1}/{self.args.count}] {config.as_label()}")

            result = self._evaluate_config(config)

            if result.success:
                metrics = result.metrics_dict()
                metrics["success"] = 1
                metrics["trial_index"] = i
                wandb.log(metrics)
                for key, val in metrics.items():
                    wandb.summary[key] = val
                wandb.summary["config_label"] = config.as_label()
                print(
                    f"  {self.args.metric}={fmt(result.objective_value(self.args.metric))}"
                )
            else:
                wandb.log({"success": 0, "trial_index": i})
                wandb.summary["error"] = result.error or "unknown"
                print(f"  FAILED: {result.error}")

            wandb.finish()

        print(f"\nAll {self.args.count} runs logged to W&B project: {self.args.project}")
        print("Open the W&B dashboard to analyze trends:")
        print(f"  https://wandb.ai/{self.args.entity or '<your-entity>'}/{self.args.project}")

    def run(self):
        """Execute the W&B sweep or manual run."""
        if self.args.manual:
            self._manual_run()
            return

        # Sweep mode
        sweep_config = self._build_sweep_config()

        # Save sweep config locally for reference
        config_path = self.out_dir / "sweep_config.json"
        with open(config_path, "w") as f:
            json.dump(sweep_config, f, indent=2)

        if self.args.sweep_id:
            sweep_id = self.args.sweep_id
            print(f"Joining existing sweep: {sweep_id}")
        else:
            sweep_id = wandb.sweep(
                sweep=sweep_config,
                project=self.args.project,
                entity=self.args.entity,
            )
            print(f"Created sweep: {sweep_id}")
            # Save sweep ID for later reference
            (self.out_dir / "sweep_id.txt").write_text(sweep_id)

        print(f"Method: {self.args.method}")
        print(f"Metric: {self.args.metric} ({OBJECTIVES[self.args.metric]})")
        print(f"Count: {self.args.count}")
        print(f"Local logs: {self.out_dir}")
        print(f"Dashboard: https://wandb.ai/{self.args.entity or '<entity>'}/{self.args.project}/sweeps/{sweep_id}")
        print()

        wandb.agent(
            sweep_id,
            function=self._sweep_train_fn,
            count=self.args.count,
            project=self.args.project,
            entity=self.args.entity,
        )

        print(f"\nSweep complete. {self.args.count} runs evaluated.")
        print(f"View results at: https://wandb.ai/{self.args.entity or '<entity>'}/{self.args.project}/sweeps/{sweep_id}")

        self._print_trend_analysis_guide()

    def _print_trend_analysis_guide(self):
        """Print instructions for trend analysis in the W&B dashboard."""
        print("\n" + "=" * 70)
        print("TREND ANALYSIS GUIDE")
        print("=" * 70)
        print("""
After the sweep completes, open the W&B dashboard to discover trends:

1. PARALLEL COORDINATES PLOT
   - Shows all hyperparameters as vertical axes with lines connecting
     each run's values.
   - Color by the target metric to see which parameter combinations
     lead to best performance.
   - Filter to top-performing runs to identify the optimal region.

2. PARAMETER IMPORTANCE
   - W&B computes correlation between each hyperparameter and the
     target metric.
   - Identifies which parameters have the strongest impact on
     performance.

3. SCATTER PLOTS
   - Create scatter plots of metric vs. each parameter.
   - Look for trends: e.g., does increasing stage1_threads always
     improve stage1_total_fps? Is there a diminishing return?
   - Identify parameter thresholds and plateaus.

4. CUSTOM PANELS
   - Create grouped bar charts to compare batch_size categories.
   - Plot stage1_total_fps vs. stage2_total_fps to find balanced
     configurations.
   - Add a table panel showing the top-N configurations sorted by
     your metric.

5. REPORTS
   - Use W&B Reports to create a shareable document with embedded
     charts, tables, and analysis text.
   - Export data as CSV for further analysis.

Key questions to answer through trend analysis:
  - Which parameter has the greatest impact on pipeline_e2e_s?
  - Is there an optimal batch_size, or does it depend on thread count?
  - What is the relationship between stage1 and stage2 thread counts?
  - Does increasing callback_batch always help, or is there a plateau?
  - What is the interaction effect between batch_size and callback_batch?
""")


def main():
    args = parse_args()
    agent = WandBSweepAgent(args)
    agent.run()


if __name__ == "__main__":
    main()
