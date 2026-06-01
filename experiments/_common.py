"""
Shared helpers for Drava runtime characterization experiments (E1..E5).

These helpers:
  * locate examples/ apps and benchmark scripts,
  * parse [drava-metrics] log lines uniformly,
  * decompose end-to-end latency into the components defined by the paper,
  * write per-experiment CSV summaries with a stable schema.

The latency decomposition used across all experiments is:

    end_to_end_s = transport_in_s + microbatching_wait_s
                 + dispatch_overhead_s + callback_compute_s
                 + publish_s + transport_out_s

We approximate the components from existing runtime counters:

    callback_compute_s  = compute_total_s
    publish_s           = publish_total_s
    microbatching_wait  = max(0, cb_total_s - compute_total_s - publish_total_s)
    transport_in/out_s  = max(0, end_to_end_s - stage_total_s)   (lumped)
    dispatch_overhead   = max(0, stage_total_s - cb_total_s)

Any component that requires runtime instrumentation that isn't yet built
(see paper Experiments 2 and 5) is set to None and the driver records a
'requires_runtime_change' note in its CSV.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"
PTYCHO_DIR = EXAMPLES / "ptychonn"
TOMOGAN_DIR = EXAMPLES / "tomogan"

DRAVA_METRICS_RE = re.compile(
    r"\[drava-metrics\]\s+reason=(?P<reason>\S+)\s+rx_msgs=(?P<rx_msgs>\d+)\s+"
    r"rx_items=(?P<rx_items>\d+)\s+rx_bytes=(?P<rx_bytes>\d+)\s+tx_msgs=(?P<tx_msgs>\d+)\s+"
    r"tx_bytes=(?P<tx_bytes>\d+)\s+cb_batches=(?P<cb_batches>\d+)\s+cb_avg_ms=(?P<cb_avg_ms>[0-9.]+)\s+"
    r"stage_samples=(?P<stage_samples>\d+)\s+stage_avg_ms=(?P<stage_avg_ms>[0-9.]+)\s+"
    r"stage_max_ms=(?P<stage_max_ms>[0-9.]+)\s+rx_item_fps=(?P<rx_item_fps>[0-9.]+)\s+"
    r"tx_msg_fps=(?P<tx_msg_fps>[0-9.]+)\s+cb_total_s=(?P<cb_total_s>[0-9.]+)\s+"
    r"publish_total_s=(?P<publish_total_s>[0-9.]+)\s+compute_total_s=(?P<compute_total_s>[0-9.]+)\s+"
    r"stage_total_s=(?P<stage_total_s>[0-9.]+)\s+stage_total_fps=(?P<stage_total_fps>[0-9.]+)\s+"
    r"stage=(?P<stage>\S+)"
)

PUB_DONE_RE = re.compile(
    r"Done:\s+published\s+(?P<frames>\d+)\s+frames\s+in\s+(?P<time>[0-9.]+)s\s+"
    r"\(avg_fps=(?P<fps>[0-9.]+)\)"
)

# Optional triggers/markers we hope future C++ instrumentation emits.
# Until the runtime exposes them, drivers fall back to None.
FLUSH_TRIGGER_RE = re.compile(
    r"\[drava-flush\]\s+stage=(?P<stage>\S+)\s+reason=(?P<reason>threshold|eos|timeout)\s+"
    r"size=(?P<size>\d+)"
)


@dataclass
class StageMetrics:
    """Parsed [drava-metrics] for one stage at end-of-stream."""
    stage: str
    rx_msgs: int = 0
    rx_items: int = 0
    rx_bytes: int = 0
    tx_msgs: int = 0
    tx_bytes: int = 0
    cb_batches: int = 0
    cb_avg_ms: float = 0.0
    stage_samples: int = 0
    stage_avg_ms: float = 0.0
    stage_max_ms: float = 0.0
    rx_item_fps: float = 0.0
    tx_msg_fps: float = 0.0
    cb_total_s: float = 0.0
    publish_total_s: float = 0.0
    compute_total_s: float = 0.0
    stage_total_s: float = 0.0
    stage_total_fps: float = 0.0

    @classmethod
    def from_match(cls, gd: dict) -> "StageMetrics":
        return cls(
            stage=gd["stage"],
            rx_msgs=int(gd["rx_msgs"]),
            rx_items=int(gd["rx_items"]),
            rx_bytes=int(gd["rx_bytes"]),
            tx_msgs=int(gd["tx_msgs"]),
            tx_bytes=int(gd["tx_bytes"]),
            cb_batches=int(gd["cb_batches"]),
            cb_avg_ms=float(gd["cb_avg_ms"]),
            stage_samples=int(gd["stage_samples"]),
            stage_avg_ms=float(gd["stage_avg_ms"]),
            stage_max_ms=float(gd["stage_max_ms"]),
            rx_item_fps=float(gd["rx_item_fps"]),
            tx_msg_fps=float(gd["tx_msg_fps"]),
            cb_total_s=float(gd["cb_total_s"]),
            publish_total_s=float(gd["publish_total_s"]),
            compute_total_s=float(gd["compute_total_s"]),
            stage_total_s=float(gd["stage_total_s"]),
            stage_total_fps=float(gd["stage_total_fps"]),
        )


@dataclass
class FlushTriggerCounts:
    threshold: int = 0
    eos: int = 0
    timeout: int = 0

    def total(self) -> int:
        return self.threshold + self.eos + self.timeout


@dataclass
class LatencyDecomp:
    """Latency components in seconds. None means 'not measurable yet'."""
    end_to_end_s: Optional[float] = None
    transport_lumped_s: Optional[float] = None
    microbatching_wait_s: Optional[float] = None
    dispatch_overhead_s: Optional[float] = None
    callback_compute_s: Optional[float] = None
    publish_s: Optional[float] = None

    @classmethod
    def from_stage(cls, m: StageMetrics, end_to_end_s: Optional[float]) -> "LatencyDecomp":
        compute = m.compute_total_s
        publish = m.publish_total_s
        cb = m.cb_total_s
        stage = m.stage_total_s
        microbatch_wait = max(0.0, cb - compute - publish) if cb > 0 else 0.0
        dispatch_overhead = max(0.0, stage - cb) if stage > 0 else 0.0
        transport = (
            max(0.0, end_to_end_s - stage) if (end_to_end_s and stage) else None
        )
        return cls(
            end_to_end_s=end_to_end_s,
            transport_lumped_s=transport,
            microbatching_wait_s=microbatch_wait,
            dispatch_overhead_s=dispatch_overhead,
            callback_compute_s=compute,
            publish_s=publish,
        )


# ---------- subprocess helpers ----------

def stream_lines(proc: subprocess.Popen, log_path: Path,
                 line_cb: Optional[Callable[[str], None]] = None) -> None:
    if proc.stdout is None:
        return
    with open(log_path, "w", encoding="utf-8") as f:
        for line in proc.stdout:
            f.write(line)
            f.flush()
            if line_cb is not None:
                line_cb(line.rstrip("\n"))


def terminate_proc(proc: subprocess.Popen, grace_s: float = 3.0) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=grace_s)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def tail_text(path: Path, n: int = 60) -> str:
    if not path.exists():
        return "<no log>"
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:])


# ---------- benchmark wrappers ----------

def run_ptychonn_benchmark(
    out_dir: Path,
    *,
    batches: list[int],
    stage1_threads: int,
    stage2_threads: int,
    stage1_callback_batch: int,
    stage2_callback_batch: int,
    timeout_ms: int,
    rate_hz: float,
    num_frames: int,
    runs: int = 1,
    extra_args: Optional[list[str]] = None,
    extra_env: Optional[dict[str, str]] = None,
    python: Optional[str] = None,
) -> Path:
    """Invoke examples/ptychonn/benchmark_two_stages.py and return the run dir
    that contains its summary.csv."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        python or sys.executable,
        "benchmark_two_stages.py",
        "--batches", ",".join(str(b) for b in batches),
        "--stage1-threads", str(stage1_threads),
        "--stage2-threads", str(stage2_threads),
        "--stage1-callback-batch", str(stage1_callback_batch),
        "--stage2-callback-batch", str(stage2_callback_batch),
        "--timeout-ms", str(timeout_ms),
        "--rate-hz", str(rate_hz),
        "--num-frames", str(num_frames),
        "--runs", str(runs),
        "--out-dir", str(out_dir.resolve()),
    ]
    if extra_args:
        cmd.extend(extra_args)
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    print(f"[exp] $ cd {PTYCHO_DIR} && {' '.join(cmd)}")
    subprocess.run(cmd, cwd=PTYCHO_DIR, env=env, check=True)
    # benchmark_two_stages.py writes into <out_dir>/<timestamp>/summary.csv
    runs_subdirs = sorted([p for p in out_dir.iterdir() if p.is_dir()])
    if not runs_subdirs:
        raise RuntimeError(f"No timestamp run dir produced under {out_dir}")
    return runs_subdirs[-1]


def run_tomogan_benchmark(
    out_dir: Path,
    *,
    batches: list[int],
    threads: int,
    timeout_ms: int,
    rate_hz: float,
    num_frames: int,
    runs: int = 1,
    extra_args: Optional[list[str]] = None,
    extra_env: Optional[dict[str, str]] = None,
    python: Optional[str] = None,
) -> Path:
    """Invoke examples/tomogan/benchmark.py and return the timestamped run dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        python or sys.executable,
        "benchmark.py",
        "--batches", ",".join(str(b) for b in batches),
        "--threads", str(threads),
        "--timeout-ms", str(timeout_ms),
        "--rate-hz", str(rate_hz),
        "--num-frames", str(num_frames),
        "--runs", str(runs),
        "--out-dir", str(out_dir.resolve()),
    ]
    if extra_args:
        cmd.extend(extra_args)
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    print(f"[exp] $ cd {TOMOGAN_DIR} && {' '.join(cmd)}")
    subprocess.run(cmd, cwd=TOMOGAN_DIR, env=env, check=True)
    runs_subdirs = sorted([p for p in out_dir.iterdir() if p.is_dir()])
    if not runs_subdirs:
        raise RuntimeError(f"No timestamp run dir produced under {out_dir}")
    return runs_subdirs[-1]


def read_summary_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise RuntimeError(f"No summary.csv at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- log re-parsing ----------

def parse_metrics_from_log(log_path: Path) -> Optional[StageMetrics]:
    """Pick the EOS [drava-metrics] line out of an app log."""
    if not log_path.exists():
        return None
    last: Optional[StageMetrics] = None
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = DRAVA_METRICS_RE.search(line)
        if not m:
            continue
        gd = m.groupdict()
        if gd.get("reason") in ("rx_eos", "tx_eos"):
            last = StageMetrics.from_match(gd)
    return last


def parse_flush_triggers_from_log(log_path: Path) -> FlushTriggerCounts:
    """Counts [drava-flush] markers if present (Exp 2 only)."""
    counts = FlushTriggerCounts()
    if not log_path.exists():
        return counts
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = FLUSH_TRIGGER_RE.search(line)
        if not m:
            continue
        reason = m.group("reason")
        if reason == "threshold":
            counts.threshold += 1
        elif reason == "eos":
            counts.eos += 1
        elif reason == "timeout":
            counts.timeout += 1
    return counts


# ---------- CSV writer ----------

def write_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})


# ---------- timestamped output dir ----------

def make_run_dir(experiment_id: str) -> Path:
    import datetime as dt
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPO_ROOT / "experiments" / "results" / f"{experiment_id}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    return out
