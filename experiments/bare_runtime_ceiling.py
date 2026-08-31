#!/usr/bin/env python3
"""
SC Experiment 5: bare runtime throughput/latency ceiling.

This benchmark isolates Drava's maximum application-cycle rate by removing
dataset generation and model compute. The publisher reuses one cached payload,
the stage follows the normal Drava listen/callback/EOS path, and the callback
launches configurable blank GPU work before optionally publishing cached output
payloads.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
BARE_DIR = REPO_ROOT / "examples" / "bare_runtime"
RESULTS_DIR = REPO_ROOT / "experiments" / "results"

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
BACKEND_RE = re.compile(r"\[bare-runtime\]\s+backend=(?P<backend>\S+)")


def parse_ints(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError(f"empty integer list: {raw!r}")
    return vals


def parse_bools(raw: str) -> list[bool]:
    vals = []
    for item in raw.split(","):
        text = item.strip().lower()
        if not text:
            continue
        if text in ("0", "false", "no", "off"):
            vals.append(False)
        elif text in ("1", "true", "yes", "on"):
            vals.append(True)
        else:
            raise ValueError(f"invalid boolean value: {item!r}")
    if not vals:
        raise ValueError(f"empty boolean list: {raw!r}")
    return vals


def make_run_dir(prefix: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RESULTS_DIR / f"{prefix}_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_run_config(
    path: Path,
    *,
    run_tag: str,
    nats_url: str,
    batch: int,
    threads: int,
    fetch_batch: int,
    timeout_ms: int,
    callback_serialize: bool,
    num_frames: int,
    rate_hz: float,
    payload_bytes: int,
) -> None:
    callback_serialize_text = "true" if callback_serialize else "false"
    path.write_text(
        "\n".join([
            "pipeline:",
            f"  name: bare_runtime_{run_tag}",
            "",
            "transport:",
            "  type: nats",
            f"  nats_url: {nats_url}",
            "",
            "publisher:",
            f"  num_frames: {num_frames}",
            f"  rate_hz: {rate_hz}",
            f"  payload_bytes: {payload_bytes}",
            "",
            "stages:",
            "  - name: stage1",
            "    runtime:",
            f"      threads: {threads}",
            f"      callback_batch: {batch}",
            f"      callback_serialize: {callback_serialize_text}",
            "    ingress:",
            f"      stream: FRAMES_{run_tag}",
            f"      subject: frames.raw.{run_tag}",
            f"      durable: drava_bare_stage1_{run_tag}",
            f"      fetch_batch: {fetch_batch}",
            f"      fetch_timeout_ms: {timeout_ms}",
            "    egress:",
            f"      stream: OUTPUT_{run_tag}",
            f"      subject: frames.out.{run_tag}",
            "",
        ]),
        encoding="utf-8",
    )


def write_nats_config(path: Path, store_dir: Path, nats_url: str, max_payload_bytes: int) -> None:
    parsed = urlparse(nats_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 4222
    if host == "127.0.0.1":
        host = "0.0.0.0"
    store = str(store_dir.resolve()).replace('"', '\\"')
    path.write_text(
        "\n".join([
            f"host: {host}",
            f"port: {port}",
            "http_port: 8222",
            f"max_payload: {max_payload_bytes}",
            "",
            "jetstream {",
            f'    store_dir: "{store}"',
            "}",
            "",
        ]),
        encoding="utf-8",
    )


def start_nats(args, run_dir: Path, nats_url: str, max_payload_bytes: int):
    nats_config = args.nats_config
    if nats_config is None:
        nats_config = run_dir / "nats.generated.conf"
        write_nats_config(nats_config, run_dir / "nats-store", nats_url, max_payload_bytes)
    cmd = [args.nats_command, "-c", str(nats_config.resolve())]
    log_path = run_dir / "nats.log"
    f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
    return proc, f, log_path


def wait_for_log_line(path: Path, pattern: str, timeout_s: float) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if pattern in text:
                return True
            if "address already in use" in text.lower():
                return False
        time.sleep(0.2)
    return False


def terminate_proc(proc: subprocess.Popen, grace_s: float = 3.0) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=grace_s)
    except Exception:
        try:
            proc.terminate()
            proc.wait(timeout=grace_s)
        except Exception:
            proc.kill()


def stream_lines(proc, log_path: Path, line_cb=None) -> None:
    with open(log_path, "w", encoding="utf-8") as f:
        for line in proc.stdout:
            f.write(line)
            f.flush()
            if line_cb is not None:
                line_cb(line.rstrip("\n"))


def tail_text(path: Path, n: int = 80) -> str:
    if not path.exists():
        return "<no log file>"
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:])


def fnum(row: dict, key: str) -> float | None:
    value = row.get(key)
    if value in ("", None):
        return None
    return float(value)


def mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def stdev(vals: list[float]) -> float | None:
    if not vals:
        return None
    if len(vals) == 1:
        return 0.0
    mu = mean(vals)
    assert mu is not None
    return math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))


def run_one(args, run_dir: Path, cell: dict, run_idx: int) -> dict:
    batch = cell["batch"]
    threads = cell["threads"]
    payload_bytes = cell["payload_bytes"]
    callback_serialize = cell["callback_serialize"]
    fetch_batch = args.fetch_batch if args.fetch_batch > 0 else batch

    run_tag = (
        f"{run_dir.name}_b{batch}_t{threads}_p{payload_bytes}_"
        f"s{1 if callback_serialize else 0}_r{run_idx}"
    )
    run_config_path = run_dir / f"pipeline_{run_tag}.yaml"
    write_run_config(
        run_config_path,
        run_tag=run_tag,
        nats_url=args.nats_url,
        batch=batch,
        threads=threads,
        fetch_batch=fetch_batch,
        timeout_ms=args.timeout_ms,
        callback_serialize=callback_serialize,
        num_frames=args.num_frames,
        rate_hz=args.rate_hz,
        payload_bytes=payload_bytes,
    )

    env = dict(os.environ)
    env.update({
        "XKAAPI_VERBOSE": str(args.xkaapi_verbose),
        "DRAVA_STAGE_CONFIG": str(run_config_path),
        "DRAVA_STAGE_NAME": "stage1",
        "DRAVA_THREADS": str(threads),
        "DRAVA_CALLBACK_BATCH": str(batch),
        "DRAVA_CALLBACK_SERIALIZE": "1" if callback_serialize else "0",
        "DRAVA_CALLBACK_FLUSH_TIMEOUT_MS": str(args.callback_flush_timeout_ms),
        "DRAVA_PUBLISH_NUM_FRAMES": str(args.num_frames),
        "DRAVA_PUBLISH_RATE_HZ": str(args.rate_hz),
        "DRAVA_PUBLISH_INFLIGHT": str(args.publish_inflight),
        "DRAVA_PUBLISH_LOG_EVERY": str(args.publish_log_every),
        "DRAVA_BARE_PAYLOAD_BYTES": str(payload_bytes),
        "DRAVA_BARE_OUTPUT_PAYLOAD_BYTES": str(args.output_payload_bytes or payload_bytes),
        "DRAVA_BARE_GPU_BACKEND": args.gpu_backend,
        "DRAVA_BARE_KERNEL_LAUNCHES": str(args.kernel_launches),
        "DRAVA_BARE_KERNEL_BLOCKS": str(args.kernel_blocks),
        "DRAVA_BARE_KERNEL_THREADS": str(args.kernel_threads),
        "DRAVA_BARE_GPU_SYNC": "1" if args.gpu_sync else "0",
        "DRAVA_BARE_PUBLISH_MODE": args.publish_mode,
        "DRAVA_BARE_WARMUP_RUNS": str(args.warmup_runs),
    })

    app_log = run_dir / f"app_{run_tag}.log"
    pub_log = run_dir / f"pub_{run_tag}.log"
    app_ready = threading.Event()
    app_metrics = {}
    pub_done = {}
    marks = {"publish_start": None, "metrics": None}
    selected_backend = None

    def on_app_line(line: str):
        nonlocal selected_backend
        if "JetStream ready:" in line:
            app_ready.set()
        m_backend = BACKEND_RE.search(line)
        if m_backend:
            selected_backend = m_backend.group("backend")
        m = DRAVA_METRICS_RE.search(line)
        if m:
            gd = m.groupdict()
            if gd.get("reason") in ("rx_eos", "tx_eos"):
                app_metrics.update(gd)
                marks["metrics"] = time.monotonic()

    def on_pub_line(line: str):
        m = PUB_DONE_RE.search(line)
        if m:
            pub_done.update(m.groupdict())

    app_proc = subprocess.Popen(
        [args.python, "app.py"],
        cwd=BARE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    app_thread = threading.Thread(target=stream_lines, args=(app_proc, app_log, on_app_line), daemon=True)
    app_thread.start()

    ready_deadline = time.time() + args.startup_timeout_s
    while time.time() < ready_deadline:
        if app_ready.is_set():
            break
        if app_proc.poll() is not None:
            raise RuntimeError(f"app exited early\n--- app tail ---\n{tail_text(app_log)}")
        time.sleep(0.2)
    if not app_ready.is_set():
        terminate_proc(app_proc)
        app_thread.join(timeout=5)
        raise RuntimeError(f"app startup timed out\n--- app tail ---\n{tail_text(app_log)}")

    marks["publish_start"] = time.monotonic()
    pub_proc = subprocess.Popen(
        [args.python, "publisher_jetstream.py"],
        cwd=BARE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log, on_pub_line), daemon=True)
    pub_thread.start()
    pub_timeout_s = max(args.publisher_timeout_s, int(max(1, args.num_frames) / 1000) + 120)
    pub_proc.wait(timeout=pub_timeout_s)
    pub_thread.join(timeout=5)

    end_wait = time.time() + args.app_timeout_s
    while time.time() < end_wait and not app_metrics:
        if app_proc.poll() is not None:
            break
        time.sleep(0.2)

    terminate_proc(app_proc)
    app_thread.join(timeout=5)

    if not pub_done:
        raise RuntimeError(f"publisher final line not found\n--- pub tail ---\n{tail_text(pub_log)}")
    if not app_metrics:
        raise RuntimeError(f"drava metrics line not found\n--- app tail ---\n{tail_text(app_log)}")

    publisher_frames = int(pub_done["frames"])
    rx_items = int(app_metrics["rx_items"])
    if publisher_frames != rx_items:
        raise RuntimeError(f"frame mismatch: publisher={publisher_frames} stage={rx_items}")

    e2e_s = (marks["metrics"] or time.monotonic()) - marks["publish_start"]
    stage_total_s = float(app_metrics["stage_total_s"])
    runtime_gap_s = max(0.0, e2e_s - stage_total_s)
    return {
        "experiment": "bare_runtime_ceiling",
        "config": f"b{batch}_t{threads}_p{payload_bytes}_s{1 if callback_serialize else 0}",
        "run": run_idx,
        "batch": batch,
        "threads": threads,
        "fetch_batch": fetch_batch,
        "timeout_ms": args.timeout_ms,
        "payload_bytes": payload_bytes,
        "output_payload_bytes": args.output_payload_bytes or payload_bytes,
        "callback_serialize": int(callback_serialize),
        "gpu_backend_requested": args.gpu_backend,
        "gpu_backend_selected": selected_backend or "",
        "kernel_launches": args.kernel_launches,
        "kernel_blocks": args.kernel_blocks,
        "kernel_threads": args.kernel_threads,
        "gpu_sync": int(args.gpu_sync),
        "publish_mode": args.publish_mode,
        "rate_hz": args.rate_hz,
        "frames": publisher_frames,
        "publisher_time_s": float(pub_done["time"]),
        "publisher_fps": float(pub_done["fps"]),
        "pipeline_e2e_s": e2e_s,
        "pipeline_fps": publisher_frames / e2e_s if e2e_s > 0 else "",
        "stage_total_s": stage_total_s,
        "stage_total_fps": float(app_metrics["stage_total_fps"]),
        "runtime_gap_s": runtime_gap_s,
        "runtime_gap_pct": runtime_gap_s / e2e_s * 100.0 if e2e_s > 0 else "",
        "rx_msgs": int(app_metrics["rx_msgs"]),
        "rx_items": rx_items,
        "rx_bytes": int(app_metrics["rx_bytes"]),
        "tx_msgs": int(app_metrics["tx_msgs"]),
        "tx_bytes": int(app_metrics["tx_bytes"]),
        "callback_batches": int(app_metrics["cb_batches"]),
        "cb_avg_ms": float(app_metrics["cb_avg_ms"]),
        "stage_samples": int(app_metrics["stage_samples"]),
        "stage_avg_ms": float(app_metrics["stage_avg_ms"]),
        "stage_max_ms": float(app_metrics["stage_max_ms"]),
        "cb_total_s": float(app_metrics["cb_total_s"]),
        "compute_total_s": float(app_metrics["compute_total_s"]),
        "publish_total_s": float(app_metrics["publish_total_s"]),
        "app_log": str(app_log),
        "publisher_log": str(pub_log),
    }


RAW_COLUMNS = [
    "experiment", "config", "run", "batch", "threads", "fetch_batch", "timeout_ms",
    "payload_bytes", "output_payload_bytes", "callback_serialize",
    "gpu_backend_requested", "gpu_backend_selected", "kernel_launches",
    "kernel_blocks", "kernel_threads", "gpu_sync", "publish_mode", "rate_hz",
    "frames", "publisher_time_s", "publisher_fps", "pipeline_e2e_s",
    "pipeline_fps", "stage_total_s", "stage_total_fps", "runtime_gap_s",
    "runtime_gap_pct", "rx_msgs", "rx_items", "rx_bytes", "tx_msgs", "tx_bytes",
    "callback_batches", "cb_avg_ms", "stage_samples", "stage_avg_ms",
    "stage_max_ms", "cb_total_s", "compute_total_s", "publish_total_s",
    "app_log", "publisher_log",
]


def write_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def summarize(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["batch"], row["threads"], row["payload_bytes"], row["callback_serialize"])].append(row)

    out = []
    for (batch, threads, payload_bytes, callback_serialize), group in sorted(groups.items()):
        def vals(key: str) -> list[float]:
            return [float(r[key]) for r in group if r.get(key) not in ("", None)]

        out.append({
            "experiment": "bare_runtime_ceiling",
            "config": group[0]["config"],
            "batch": batch,
            "threads": threads,
            "payload_bytes": payload_bytes,
            "callback_serialize": callback_serialize,
            "runs": len(group),
            "frames": group[0]["frames"],
            "gpu_backend_selected": group[0]["gpu_backend_selected"],
            "publish_mode": group[0]["publish_mode"],
            "pipeline_fps_mean": mean(vals("pipeline_fps")),
            "pipeline_fps_std": stdev(vals("pipeline_fps")),
            "stage_total_fps_mean": mean(vals("stage_total_fps")),
            "stage_total_fps_std": stdev(vals("stage_total_fps")),
            "pipeline_e2e_s_mean": mean(vals("pipeline_e2e_s")),
            "cb_avg_ms_mean": mean(vals("cb_avg_ms")),
            "stage_avg_ms_mean": mean(vals("stage_avg_ms")),
            "stage_max_ms_mean": mean(vals("stage_max_ms")),
            "compute_total_s_mean": mean(vals("compute_total_s")),
            "publish_total_s_mean": mean(vals("publish_total_s")),
            "runtime_gap_pct_mean": mean(vals("runtime_gap_pct")),
        })
    return out


AGG_COLUMNS = [
    "experiment", "config", "batch", "threads", "payload_bytes",
    "callback_serialize", "runs", "frames", "gpu_backend_selected",
    "publish_mode", "pipeline_fps_mean", "pipeline_fps_std",
    "stage_total_fps_mean", "stage_total_fps_std", "pipeline_e2e_s_mean",
    "cb_avg_ms_mean", "stage_avg_ms_mean", "stage_max_ms_mean",
    "compute_total_s_mean", "publish_total_s_mean", "runtime_gap_pct_mean",
]


def print_table(rows: list[dict]) -> None:
    print("")
    print("| Batch | Threads | Payload B | Ser | Frames | Pipeline FPS | Stage FPS | cb avg ms | Stage max ms | Backend |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in rows:
        print(
            f"| {row['batch']} | {row['threads']} | {row['payload_bytes']} | "
            f"{row['callback_serialize']} | {row['frames']} | "
            f"{float(row['pipeline_fps']):.2f} | {float(row['stage_total_fps']):.2f} | "
            f"{float(row['cb_avg_ms']):.3f} | {float(row['stage_max_ms']):.3f} | "
            f"{row['gpu_backend_selected']} |"
        )


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batches", default="1,8,32,128,256,512",
                   help="Comma-separated Drava callback batch sizes.")
    p.add_argument("--thread-list", default="1,2,4,8",
                   help="Comma-separated Drava runtime thread counts.")
    p.add_argument("--payload-bytes", default="1",
                   help="Comma-separated cached input payload sizes.")
    p.add_argument("--callback-serialize-list", default="0",
                   help="Comma-separated serialize modes, e.g. 0 or 0,1.")
    p.add_argument("--fetch-batch", type=int, default=0,
                   help="JetStream fetch batch. 0 means match callback batch.")
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--callback-flush-timeout-ms", type=int, default=0)
    p.add_argument("--num-frames", type=int, default=100000)
    p.add_argument("--rate-hz", type=float, default=0.0,
                   help="Publisher rate. 0 means max speed.")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--reuse-nats", action="store_true")
    p.add_argument("--nats-url", default="nats://127.0.0.1:4222")
    p.add_argument("--nats-command", default="nats-server")
    p.add_argument("--nats-config", type=Path, default=None)
    p.add_argument("--xkaapi-verbose", type=int, default=4)
    p.add_argument("--gpu-backend", choices=["auto", "cupy", "torch", "none"], default="auto")
    p.add_argument("--kernel-launches", type=int, default=1)
    p.add_argument("--kernel-blocks", type=int, default=1)
    p.add_argument("--kernel-threads", type=int, default=1)
    p.add_argument("--no-gpu-sync", action="store_true")
    p.add_argument("--publish-mode", choices=["none", "one_per_callback", "one_per_frame"], default="none")
    p.add_argument("--output-payload-bytes", type=int, default=0,
                   help="Cached output payload size. 0 means match input payload.")
    p.add_argument("--publish-inflight", type=int, default=1024)
    p.add_argument("--publish-log-every", type=int, default=10000)
    p.add_argument("--warmup-runs", type=int, default=3)
    p.add_argument("--startup-timeout-s", type=float, default=120.0)
    p.add_argument("--publisher-timeout-s", type=float, default=180.0)
    p.add_argument("--app-timeout-s", type=float, default=45.0)
    return p.parse_args()


def main():
    args = parse_args()
    args.gpu_sync = not args.no_gpu_sync
    batches = parse_ints(args.batches)
    threads = parse_ints(args.thread_list)
    payload_sizes = parse_ints(args.payload_bytes)
    serialize_modes = parse_bools(args.callback_serialize_list)
    if args.num_frames <= 0:
        raise SystemExit("--num-frames must be positive")

    run_dir = make_run_dir("bare_runtime_ceiling")
    print(f"[sc5-bare-runtime] writing to {run_dir}")

    nats_proc = None
    nats_log_file = None
    if args.reuse_nats:
        print(f"[sc5-bare-runtime] reusing NATS at {args.nats_url}")
    else:
        max_payload = max(payload_sizes + [args.output_payload_bytes or 0, 1024]) + 1024
        print("[sc5-bare-runtime] starting nats-server")
        nats_proc, nats_log_file, nats_log_path = start_nats(args, run_dir, args.nats_url, max_payload)
        ok = wait_for_log_line(nats_log_path, "Listening for client connections", 20.0)
        if not ok:
            terminate_proc(nats_proc)
            if nats_log_file:
                nats_log_file.close()
            raise SystemExit(f"failed to start nats-server; see {nats_log_path}")
        print(f"[sc5-bare-runtime] nats ready ({args.nats_url})")

    cells = [
        {
            "batch": batch,
            "threads": thread_count,
            "payload_bytes": payload_bytes,
            "callback_serialize": callback_serialize,
        }
        for callback_serialize in serialize_modes
        for payload_bytes in payload_sizes
        for thread_count in threads
        for batch in batches
    ]

    rows = []
    try:
        for cell in cells:
            # The NATS transport reserves one worker thread (tid 0) for I/O. With
            # callback_serialize=false the callback runs on the other threads, so
            # a non-serialized stage needs >= 2 threads. Skip invalid cells rather
            # than aborting the whole sweep. (serialize=true runs inline on tid 0.)
            if cell["threads"] < 2 and not cell["callback_serialize"]:
                print(
                    f"[sc5-bare-runtime] skip batch={cell['batch']} "
                    f"threads={cell['threads']} serialize=0: needs >= 2 threads "
                    f"(1 is reserved for I/O)."
                )
                continue
            for run_idx in range(1, args.runs + 1):
                print(
                    "[sc5-bare-runtime] "
                    f"batch={cell['batch']} threads={cell['threads']} "
                    f"payload={cell['payload_bytes']} serialize={int(cell['callback_serialize'])} "
                    f"run={run_idx}"
                )
                row = run_one(args, run_dir, cell, run_idx)
                rows.append(row)
                print(
                    "  done: "
                    f"pipeline_fps={float(row['pipeline_fps']):.2f} "
                    f"stage_fps={float(row['stage_total_fps']):.2f} "
                    f"cb_avg_ms={float(row['cb_avg_ms']):.3f}"
                )
        raw_path = run_dir / "bare_runtime_ceiling_summary.csv"
        agg_path = run_dir / "bare_runtime_ceiling_aggregate.csv"
        write_rows(raw_path, rows, RAW_COLUMNS)
        write_rows(agg_path, summarize(rows), AGG_COLUMNS)
        print_table(rows)
        print(f"\nWrote raw summary: {raw_path}")
        print(f"Wrote aggregate summary: {agg_path}")
    except BaseException:
        print(f"\nLogs written to: {run_dir}")
        raise
    finally:
        if nats_proc is not None:
            print("[sc5-bare-runtime] stopping nats-server")
            terminate_proc(nats_proc)
        if nats_log_file is not None:
            nats_log_file.close()


if __name__ == "__main__":
    main()
