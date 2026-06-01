"""
Shared benchmark runner for Drava PtychoNN agents.

Wraps benchmark_two_stages.py as a subprocess and parses its output to extract
pipeline metrics. Both Agent 1 (guided exploration) and Agent 2 (W&B sweep)
use this module to evaluate hyperparameter configurations.
"""

import csv
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

SUMMARY_PATH_RE = re.compile(r"Logs and summary written to:\s+(?P<path>\S+)")

# Hyperparameter space definition with bounds and types.
# Used by both agents for consistent parameter ranges.
PARAM_SPACE = {
    "batch_size": {
        "type": "categorical",
        "choices": [64, 128, 256, 512, 1024],
        "default": [256, 512],
    },
    "stage1_threads": {
        "type": "int",
        "low": 1,
        "high": 32,
        "default_choices": [4, 8, 10, 20],
    },
    "stage2_threads": {
        "type": "int",
        "low": 1,
        "high": 16,
        "default_choices": [1, 2, 4],
    },
    "stage1_callback_batch": {
        "type": "categorical",
        "choices": [32, 64, 128, 256, 512, 1024],
        "default": [256, 512],
    },
    "stage2_callback_batch": {
        "type": "categorical",
        "choices": [16, 32, 64, 128, 256, 512],
        "default": [64, 128, 256],
    },
    "rate_hz": {
        "type": "float",
        "low": 0.0,
        "high": 50000.0,
        "default_choices": [0.0],
        "description": "Publisher rate in Hz. 0 = max speed (no pacing).",
    },
}

# Metrics extracted from each benchmark run.
METRIC_KEYS = [
    "pipeline_e2e_s",
    "stage1_total_fps",
    "stage2_total_fps",
    "publisher_avg_fps",
    "stage1_total_time_s",
    "stage2_total_time_s",
    "publisher_time_s",
]

# Objectives and their optimization direction.
OBJECTIVES = {
    "pipeline_e2e_s": "minimize",
    "stage1_total_fps": "maximize",
    "stage2_total_fps": "maximize",
}


@dataclass
class RunConfig:
    """A single hyperparameter configuration to evaluate."""
    batch_size: int = 256
    stage1_threads: int = 4
    stage2_threads: int = 4
    stage1_callback_batch: int = 256
    stage2_callback_batch: int = 64
    rate_hz: float = 0.0

    def as_label(self) -> str:
        return (
            f"b{self.batch_size}_s1t{self.stage1_threads}_s2t{self.stage2_threads}"
            f"_s1cb{self.stage1_callback_batch}_s2cb{self.stage2_callback_batch}"
            f"_r{str(self.rate_hz).replace('.', '_')}"
        )


@dataclass
class RunResult:
    """Metrics from a single benchmark execution."""
    config: RunConfig
    success: bool = False
    pipeline_e2e_s: Optional[float] = None
    stage1_total_fps: Optional[float] = None
    stage2_total_fps: Optional[float] = None
    publisher_avg_fps: Optional[float] = None
    stage1_total_time_s: Optional[float] = None
    stage2_total_time_s: Optional[float] = None
    publisher_time_s: Optional[float] = None
    total_frames: Optional[int] = None
    summary_path: Optional[str] = None
    error: Optional[str] = None

    def objective_value(self, objective: str) -> Optional[float]:
        return getattr(self, objective, None)

    def metrics_dict(self) -> dict:
        """Return all numeric metrics as a flat dict (for logging)."""
        d = {}
        for k in METRIC_KEYS:
            v = getattr(self, k, None)
            if v is not None:
                d[k] = v
        if self.total_frames is not None:
            d["total_frames"] = self.total_frames
        return d


def _load_summary_csv(summary_csv: Path) -> dict:
    """Parse the summary.csv produced by benchmark_two_stages.py."""
    with open(summary_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise RuntimeError(f"No rows in summary CSV: {summary_csv}")
    row = rows[0]
    numeric_keys = {
        "batch", "run", "stage1_threads", "stage2_threads", "timeout_ms",
        "total_frames", "publisher_time_s", "publisher_avg_fps",
        "stage1_total_time_s", "stage1_total_fps", "stage2_total_time_s",
        "stage2_total_fps", "stage2_side", "pipeline_e2e_s",
    }
    out = {}
    for k, v in row.items():
        if k in numeric_keys and v not in ("", None):
            if k in {"batch", "run", "stage1_threads", "stage2_threads",
                      "timeout_ms", "total_frames", "stage2_side"}:
                out[k] = int(float(v))
            else:
                out[k] = float(v)
        else:
            out[k] = v
    return out


def run_benchmark(
    config: RunConfig,
    *,
    python: str = sys.executable,
    benchmark_script: Optional[str] = None,
    num_frames: int = 10000,
    timeout_ms: int = 200,
    runs: int = 1,
    extra_args: Optional[list] = None,
    cwd: Optional[Path] = None,
) -> RunResult:
    """
    Execute a single benchmark run with the given hyperparameters.

    Invokes benchmark_two_stages.py as a subprocess, parses its output,
    and returns a RunResult with all collected metrics.
    """
    if cwd is None:
        cwd = Path(__file__).resolve().parent.parent  # examples/ptychonn/

    if benchmark_script is None:
        benchmark_script = str(cwd / "benchmark_two_stages.py")

    cmd = [
        python,
        str(benchmark_script),
        "--batches", str(config.batch_size),
        "--runs", str(runs),
        "--stage1-threads", str(config.stage1_threads),
        "--stage2-threads", str(config.stage2_threads),
        "--stage1-callback-batch", str(config.stage1_callback_batch),
        "--stage2-callback-batch", str(config.stage2_callback_batch),
        "--timeout-ms", str(timeout_ms),
        "--num-frames", str(num_frames),
        "--rate-hz", str(config.rate_hz),
    ]
    if extra_args:
        cmd.extend(extra_args)

    result = RunResult(config=config)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=600,  # 10-minute hard timeout per run
        )
    except subprocess.TimeoutExpired:
        result.error = "benchmark subprocess timed out (600s)"
        return result

    if proc.returncode != 0:
        result.error = proc.stderr.strip() or "benchmark returned non-zero"
        return result

    m = SUMMARY_PATH_RE.search(proc.stdout)
    if not m:
        result.error = "could not find summary path in benchmark output"
        return result

    summary_dir = Path(m.group("path"))
    summary_csv = summary_dir / "summary.csv"
    if not summary_csv.exists():
        result.error = f"missing summary CSV: {summary_csv}"
        return result

    try:
        row = _load_summary_csv(summary_csv)
    except Exception as exc:
        result.error = f"failed to parse summary CSV: {exc}"
        return result

    result.success = True
    result.summary_path = str(summary_dir)
    result.pipeline_e2e_s = row.get("pipeline_e2e_s")
    result.stage1_total_fps = row.get("stage1_total_fps")
    result.stage2_total_fps = row.get("stage2_total_fps")
    result.publisher_avg_fps = row.get("publisher_avg_fps")
    result.stage1_total_time_s = row.get("stage1_total_time_s")
    result.stage2_total_time_s = row.get("stage2_total_time_s")
    result.publisher_time_s = row.get("publisher_time_s")
    result.total_frames = row.get("total_frames")

    return result


def fmt(x, spec="{:.2f}"):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return spec.format(x)
