#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

# Drava runtime metrics are read from the JSONL file the runtime writes
# (DRAVA_METRICS_FILE), and publisher metrics from the JSON file the publisher
# writes (DRAVA_PUBLISHER_METRICS_FILE). Nothing is scraped from stdout.


def read_publisher_metrics(path: Path):
    """Return the publisher's single JSON metrics object, or None if the file is
    not present/complete yet."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_metrics_record(path: Path, stage=None, reasons=("rx_eos", "tx_eos")):
    """Return the last JSON metrics record in the runtime's metrics file that
    matches the given stage and reason, or None if not present yet."""
    if not path.exists():
        return None
    record = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if reasons is not None and obj.get("reason") not in reasons:
            continue
        if stage is not None and obj.get("stage") != stage:
            continue
        record = obj
    return record


def parse_args():
    p = argparse.ArgumentParser(description="Run TomoGAN runtime and energy benchmarks.")
    p.add_argument("--batches", default="1,2,4,8,16", help="Comma-separated DRAVA_INFER_BATCH values.")
    p.add_argument("--thread-list", default="",
                   help="Optional comma-separated thread counts to sweep. Overrides --threads for the matrix.")
    p.add_argument("--timeout-ms", type=int, default=None,
                   help="Override stage ingress fetch_timeout_ms. Defaults to pipeline.yaml.")
    p.add_argument("--threads", type=int, default=None,
                   help="Override DRAVA_THREADS and stage runtime threads. Defaults to pipeline.yaml.")
    p.add_argument("--xkaapi-verbose", type=int, default=4, help="XKAAPI_VERBOSE for the app runtime.")
    p.add_argument("--rate-hz", type=float, default=None, help="DRAVA_PUBLISH_RATE_HZ (<=0 means max speed).")
    p.add_argument("--num-frames", type=int, default=0, help="Frames to publish. Defaults to YAML or dataset size.")
    p.add_argument("--runs", type=int, default=1, help="Runs per batch size.")
    p.add_argument("--python", default=sys.executable, help="Python executable to use.")
    p.add_argument("--reuse-nats", action="store_true", help="Use an existing NATS server.")
    p.add_argument("--nats-url", default="", help="NATS URL. Defaults to transport.nats_url from --stage-config.")
    p.add_argument("--nats-command", default="nats-server", help="nats-server executable when launching NATS.")
    p.add_argument("--nats-config", default="",
                   help="Optional nats-server config file. When set, launches '<nats-command> -c <file>'.")
    p.add_argument("--stage-config", default="pipeline.yaml", help="Base stage config YAML path.")
    p.add_argument("--out-dir", default="bench_logs", help="Output directory under examples/tomogan.")
    p.add_argument("--app-timeout-s", type=float, default=None, help="Max wait for app metrics after publisher exits.")
    p.add_argument("--gpu-sample-interval-s", type=float, default=0.2,
                   help="nvidia-smi sampling interval for GPU power/util/memory telemetry.")
    p.add_argument("--no-gpu-telemetry", action="store_true",
                   help="Disable nvidia-smi power/util/memory sampling. "
                        "Energy still comes from the runtime metrics file.")
    return p.parse_args()


def load_yaml_config(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"Top-level YAML config must be a mapping: {path}")
    return data


def write_yaml_config(path: Path, config: dict):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)


def section_value(config: dict, section: str, key: str, default=None):
    value = config.get(section, {})
    if isinstance(value, dict):
        return value.get(key, default)
    return default


def stage_by_name(config: dict, stage_name: str):
    for stage in config.get("stages", []):
        if isinstance(stage, dict) and stage.get("name") == stage_name:
            return stage
    raise RuntimeError(f"Stage '{stage_name}' not found in config")


def build_run_config(base_config: dict, run_tag: str, nats_url: str, batch_size: int,
                     threads: int | None, timeout_ms: int | None, rate_hz: float,
                     num_frames: int | None):
    config = {
        "pipeline": dict(base_config.get("pipeline", {})),
        "transport": dict(base_config.get("transport", {})),
        "publisher": dict(base_config.get("publisher", {})),
        "benchmark": dict(base_config.get("benchmark", {})),
        "stages": [dict(stage) for stage in base_config.get("stages", [])],
    }
    config.setdefault("pipeline", {})["name"] = f"tomogan_single_stage_{run_tag}"
    config.setdefault("transport", {})["nats_url"] = nats_url
    publisher = config.setdefault("publisher", {})
    publisher["rate_hz"] = rate_hz
    if num_frames is not None and num_frames > 0:
        publisher["num_frames"] = num_frames

    stage = stage_by_name(config, "stage1")
    runtime = dict(stage.get("runtime", {}))
    if threads is not None:
        runtime["threads"] = threads
    runtime["callback_batch"] = batch_size
    stage["runtime"] = runtime

    ingress = dict(stage.get("ingress", {}))
    ingress["stream"] = f"FRAMES_{run_tag}"
    ingress["subject"] = f"frames.raw.{run_tag}"
    ingress["durable"] = f"drava_tomogan_stage1_{run_tag}"
    ingress["fetch_batch"] = batch_size
    if timeout_ms is not None:
        ingress["fetch_timeout_ms"] = timeout_ms
    stage["ingress"] = ingress
    return config


def stream_lines(proc, log_path, line_cb=None):
    with open(log_path, "w", encoding="utf-8") as f:
        for line in proc.stdout:
            f.write(line)
            f.flush()
            if line_cb is not None:
                line_cb(line.rstrip("\n"))


def tail_text(path: Path, n: int = 60):
    if not path.exists():
        return "<no log file>"
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:])


def start_nats(args, run_dir: Path, nats_url: str):
    if args.nats_config:
        cmd = [args.nats_command, "-c", str(Path(args.nats_config).expanduser())]
        log_path = run_dir / "nats.log"
        f = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
        return proc, f, log_path

    host_port = nats_url.replace("nats://", "")
    if ":" not in host_port:
        raise RuntimeError(f"Invalid --nats-url: {nats_url}")
    host, port = host_port.rsplit(":", 1)
    cmd = [args.nats_command, "-js", "-a", host, "-p", port]
    log_path = run_dir / "nats.log"
    f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
    return proc, f, log_path


def wait_for_log_line(path: Path, pattern: str, timeout_s: float):
    end = time.time() + timeout_s
    while time.time() < end:
        if path.exists():
            txt = path.read_text(encoding="utf-8", errors="ignore")
            if pattern in txt:
                return True
            if "address already in use" in txt.lower():
                return False
        time.sleep(0.2)
    return False


def terminate_proc(proc: subprocess.Popen, grace_s=3.0):
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


def gpu_power_sampler(stop_evt: threading.Event, samples: list, interval_s: float):
    cmd = [
        "nvidia-smi",
        "--query-gpu=timestamp,power.draw,utilization.gpu,memory.used",
        "--format=csv,noheader,nounits",
    ]
    while not stop_evt.is_set():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2, check=False)
            if result.returncode == 0:
                powers = []
                utils = []
                mems = []
                for line in result.stdout.splitlines():
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) < 4:
                        continue
                    try:
                        powers.append(float(parts[1]))
                        utils.append(float(parts[2]))
                        mems.append(float(parts[3]))
                    except ValueError:
                        pass
                if powers:
                    samples.append((time.monotonic(), sum(powers), sum(utils) / len(utils), sum(mems)))
        except Exception:
            pass
        stop_evt.wait(interval_s)


def average_window(samples, start_t, end_t, index):
    values = [sample[index] for sample in samples if start_t <= sample[0] <= end_t]
    return sum(values) / len(values) if values else None


def fmt(x, f="{:.2f}"):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return f.format(x)


def parse_int_list(raw: str):
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def mean(values):
    return sum(values) / len(values) if values else None


def stdev(values):
    if len(values) < 2:
        return 0.0 if values else None
    mu = mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / (len(values) - 1))


def aggregate_rows(rows):
    groups = {}
    for row in rows:
        key = (row["batch"], row["threads"])
        groups.setdefault(key, []).append(row)

    out = []
    for (batch, threads), group in sorted(groups.items()):
        frames = group[0]["frames"]
        fps_vals = [r["stage_fps"] for r in group if r.get("stage_fps") is not None]
        e2e_vals = [r["pipeline_e2e_s"] for r in group if r.get("pipeline_e2e_s") is not None]
        overhead_pct_vals = [r["drava_overhead_pct"] for r in group if r.get("drava_overhead_pct") is not None]
        jpf_vals = [r["total_energy_j_per_frame"] for r in group if r.get("total_energy_j_per_frame") is not None]
        out.append({
            "batch": batch,
            "threads": threads,
            "runs": len(group),
            "frames": frames,
            "stage_fps_mean": mean(fps_vals),
            "stage_fps_std": stdev(fps_vals),
            "pipeline_e2e_s_mean": mean(e2e_vals),
            "drava_overhead_pct_mean": mean(overhead_pct_vals),
            "total_energy_j_per_frame_mean": mean(jpf_vals),
        })
    return out


def run_one(args, base_env, run_dir: Path, base_config: dict, batch_size: int, threads: int | None, run_idx: int):
    root = Path(__file__).resolve().parent
    nats_url = (
            args.nats_url
            or section_value(base_config, "transport", "nats_url")
            or "nats://127.0.0.1:4222"
    )
    yaml_num_frames = section_value(base_config, "publisher", "num_frames")
    yaml_rate_hz = section_value(base_config, "publisher", "rate_hz", 0.0)
    yaml_app_timeout_s = section_value(base_config, "benchmark", "app_timeout_s", 60.0)
    yaml_threads = stage_by_name(base_config, "stage1").get("runtime", {}).get("threads", 1)
    yaml_timeout_ms = stage_by_name(base_config, "stage1").get("ingress", {}).get("fetch_timeout_ms", 200)
    configured_num_frames = args.num_frames if args.num_frames > 0 else int(yaml_num_frames or 0)
    effective_app_timeout_s = args.app_timeout_s if args.app_timeout_s is not None else float(yaml_app_timeout_s)
    rate_hz = float(args.rate_hz) if args.rate_hz is not None else float(yaml_rate_hz or 0.0)
    effective_threads = threads if threads is not None else (
        args.threads if args.threads is not None else int(yaml_threads))
    effective_timeout_ms = args.timeout_ms if args.timeout_ms is not None else int(yaml_timeout_ms)

    run_tag = f"{run_dir.name}_b{batch_size}_r{run_idx}"
    run_config_path = run_dir / f"pipeline_b{batch_size}_r{run_idx}.yaml"
    write_yaml_config(
        run_config_path,
        build_run_config(
            base_config=base_config,
            run_tag=run_tag,
            nats_url=nats_url,
            batch_size=batch_size,
            threads=threads,
            timeout_ms=args.timeout_ms,
            rate_hz=rate_hz,
            num_frames=configured_num_frames if configured_num_frames > 0 else None,
        ),
    )

    env = dict(base_env)
    env["XKAAPI_VERBOSE"] = str(args.xkaapi_verbose)
    env["DRAVA_THREADS"] = str(effective_threads)
    env["DRAVA_STAGE_CONFIG"] = str(run_config_path)
    env["DRAVA_STAGE_NAME"] = "stage1"
    env["DRAVA_INFER_BATCH"] = str(batch_size)
    env["DRAVA_CALLBACK_BATCH"] = str(batch_size)
    env["DRAVA_PUBLISH_RATE_HZ"] = str(rate_hz)
    env["DRAVA_PUBLISH_INFLIGHT"] = os.getenv("DRAVA_PUBLISH_INFLIGHT", "64")
    env["DRAVA_PUBLISH_RETRIES"] = os.getenv("DRAVA_PUBLISH_RETRIES", "8")
    env["DRAVA_PUBLISH_RETRY_DELAY_S"] = os.getenv("DRAVA_PUBLISH_RETRY_DELAY_S", "0.05")
    env["DRAVA_TOMOGAN_SAVE_OUTPUT"] = os.getenv("DRAVA_TOMOGAN_SAVE_OUTPUT", "0")
    env["DRAVA_TOMOGAN_OUTPUT_PATH"] = str(run_dir / f"tomogan_output_b{batch_size}_r{run_idx}.h5")
    if configured_num_frames > 0:
        env["DRAVA_PUBLISH_NUM_FRAMES"] = str(configured_num_frames)

    app_log = run_dir / f"app_b{batch_size}_r{run_idx}.log"
    pub_log = run_dir / f"pub_b{batch_size}_r{run_idx}.log"
    metrics_path = run_dir / f"metrics_b{batch_size}_r{run_idx}.jsonl"
    pub_metrics_path = run_dir / f"pub_metrics_b{batch_size}_r{run_idx}.json"
    env["DRAVA_METRICS_FILE"] = str(metrics_path)
    app_ready = threading.Event()
    marks = {"publish_start": None, "metrics": None}

    def on_app_line(line: str):
        if "JetStream ready:" in line:
            app_ready.set()

    print(f"[batch={batch_size} run={run_idx}] starting app.py")
    app_proc = subprocess.Popen(
        [args.python, "app.py"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    app_thread = threading.Thread(target=stream_lines, args=(app_proc, app_log, on_app_line), daemon=True)
    app_thread.start()

    ready_deadline = time.time() + 180.0
    while time.time() < ready_deadline:
        if app_ready.is_set():
            break
        if app_proc.poll() is not None:
            raise RuntimeError(f"app exited early\n--- app tail ---\n{tail_text(app_log)}")
        time.sleep(0.2)

    gpu_samples = []
    gpu_stop = threading.Event()
    gpu_thread = None
    if not args.no_gpu_telemetry:
        gpu_thread = threading.Thread(
            target=gpu_power_sampler,
            args=(gpu_stop, gpu_samples, args.gpu_sample_interval_s),
            daemon=True,
        )
        gpu_thread.start()

    print(f"[batch={batch_size} run={run_idx}] starting publisher_jetstream.py")
    marks["publish_start"] = time.monotonic()
    pub_proc = subprocess.Popen(
        [args.python, "publisher_jetstream.py"],
        cwd=root,
        env=dict(env, DRAVA_PUBLISHER_METRICS_FILE=str(pub_metrics_path)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log), daemon=True)
    pub_thread.start()

    expected_frames = configured_num_frames if configured_num_frames > 0 else 16
    pub_timeout_s = max(180, int(max(1, expected_frames) / 1000) + 180)
    pub_proc.wait(timeout=pub_timeout_s)
    pub_thread.join(timeout=5)
    pub_done = read_publisher_metrics(pub_metrics_path)

    app_metrics = None
    end_wait = time.time() + effective_app_timeout_s
    while time.time() < end_wait:
        app_metrics = read_metrics_record(metrics_path, stage="stage1")
        if app_metrics is not None:
            marks["metrics"] = time.monotonic()
            break
        if app_proc.poll() is not None:
            app_metrics = read_metrics_record(metrics_path, stage="stage1")
            if app_metrics is not None:
                marks["metrics"] = time.monotonic()
            break
        time.sleep(0.2)

    gpu_stop.set()
    if gpu_thread is not None:
        gpu_thread.join(timeout=2)
    terminate_proc(app_proc)
    app_thread.join(timeout=5)

    if not pub_done:
        raise RuntimeError(f"publisher metrics file not found: {pub_metrics_path}\n--- pub tail ---\n{tail_text(pub_log)}")
    if app_metrics is None:
        raise RuntimeError(f"drava metrics not found\n--- app tail ---\n{tail_text(app_log)}")

    publisher_frames = int(pub_done["frames"])
    stage_frames = int(app_metrics["rx_items"])
    if publisher_frames != stage_frames:
        raise RuntimeError(f"frame mismatch: publisher={publisher_frames} stage1={stage_frames}")

    start_t = marks["publish_start"]
    end_t = marks["metrics"] or time.monotonic()

    # Energy comes from the runtime's exact counters (NVML for GPU, RAPL for
    # CPU), reported in the metrics JSONL over the runtime's own stage window --
    # no Python-side power sampling or integration. Fields are absent when a
    # source is unavailable (e.g. NVML not compiled in).
    gpu_energy_j = app_metrics.get("gpu_energy_j")
    cpu_energy_j = app_metrics.get("cpu_energy_j")
    total_energy_j = app_metrics.get("total_energy_j")
    total_energy_j_per_frame = app_metrics.get("total_energy_j_per_frame")

    stage_time_s = float(app_metrics["stage_total_s"])
    e2e_s = end_t - start_t
    drava_overhead_s = max(0.0, e2e_s - stage_time_s)
    drava_overhead_pct = (drava_overhead_s / e2e_s * 100.0) if e2e_s > 0 else None

    return {
        "batch": batch_size,
        "run": run_idx,
        "threads": effective_threads,
        "timeout_ms": effective_timeout_ms,
        "frames": publisher_frames,
        "publisher_time_s": float(pub_done["duration_s"]),
        "publisher_avg_fps": float(pub_done["avg_fps"]),
        "stage_time_s": stage_time_s,
        "stage_fps": float(app_metrics["stage_total_fps"]),
        "cb_avg_ms": float(app_metrics["cb_avg_ms"]),
        "pipeline_e2e_s": e2e_s,
        "drava_overhead_s": drava_overhead_s,
        "drava_overhead_pct": drava_overhead_pct,
        # GPU power/util/memory averages remain sampled telemetry (nvidia-smi);
        # energy itself is from the runtime counters above.
        "gpu_avg_power_w": average_window(gpu_samples, start_t, end_t, 1),
        "gpu_avg_util_pct": average_window(gpu_samples, start_t, end_t, 2),
        "gpu_avg_mem_mib": average_window(gpu_samples, start_t, end_t, 3),
        "gpu_energy_j": gpu_energy_j,
        "gpu_energy_j_per_frame": gpu_energy_j / publisher_frames if gpu_energy_j is not None else None,
        "cpu_energy_j": cpu_energy_j,
        "total_energy_j": total_energy_j,
        "total_energy_j_per_frame": total_energy_j_per_frame,
    }


def print_table(rows):
    print("")
    print(
        "| Batch | Threads | Frames | Stage Time (s) | Stage FPS | E2E (s) | "
        "Overhead (s) | Overhead (%) | GPU Power (W) | GPU Energy (J) | GPU J/frame | CPU Energy (J) | Total J/frame |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['batch']} | {r['threads']} | {r['frames']} | {fmt(r['stage_time_s'])} | "
            f"{fmt(r['stage_fps'])} | {fmt(r['pipeline_e2e_s'])} | "
            f"{fmt(r['drava_overhead_s'])} | {fmt(r['drava_overhead_pct'])} | "
            f"{fmt(r['gpu_avg_power_w'])} | {fmt(r['gpu_energy_j'])} | "
            f"{fmt(r['gpu_energy_j_per_frame'], '{:.4f}')} | {fmt(r['cpu_energy_j'])} | "
            f"{fmt(r['total_energy_j_per_frame'], '{:.4f}')} |"
        )


def print_aggregate_table(rows):
    print("")
    print(
        "| Batch | Threads | Runs | Frames | Stage FPS mean +/- std | E2E mean (s) | Overhead mean (%) | Total J/frame mean |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in aggregate_rows(rows):
        fps_text = "n/a"
        if r["stage_fps_mean"] is not None:
            fps_text = f"{r['stage_fps_mean']:.2f} +/- {r['stage_fps_std']:.2f}"
        print(
            f"| {r['batch']} | {r['threads']} | {r['runs']} | {r['frames']} | "
            f"{fps_text} | {fmt(r['pipeline_e2e_s_mean'])} | "
            f"{fmt(r['drava_overhead_pct_mean'])} | {fmt(r['total_energy_j_per_frame_mean'], '{:.4f}')} |"
        )


def write_summary_csv(path: Path, rows):
    columns = [
        "batch", "run", "threads", "timeout_ms", "frames", "publisher_time_s",
        "publisher_avg_fps", "stage_time_s", "stage_fps", "cb_avg_ms", "pipeline_e2e_s",
        "drava_overhead_s", "drava_overhead_pct",
        "gpu_avg_power_w", "gpu_avg_util_pct", "gpu_avg_mem_mib", "gpu_energy_j",
        "gpu_energy_j_per_frame", "cpu_energy_j", "total_energy_j",
        "total_energy_j_per_frame",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(columns) + "\n")
        for row in rows:
            f.write(",".join("" if row.get(col) is None else str(row.get(col)) for col in columns) + "\n")


def main():
    args = parse_args()
    batches = parse_int_list(args.batches)
    if not batches:
        raise SystemExit("No batch sizes provided.")
    thread_values = parse_int_list(args.thread_list) if args.thread_list else [args.threads]
    if not thread_values:
        thread_values = [None]

    root = Path(__file__).resolve().parent
    stage_config_path = (root / args.stage_config).resolve() if not Path(args.stage_config).is_absolute() else Path(
        args.stage_config)
    base_config = load_yaml_config(stage_config_path)
    nats_url = args.nats_url or section_value(base_config, "transport", "nats_url") or "nats://127.0.0.1:4222"

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / args.out_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    nats_proc = None
    nats_log_file = None
    if args.reuse_nats:
        print(f"[global] reusing existing nats ({nats_url})")
    else:
        print("[global] starting nats-server")
        nats_proc, nats_log_file, nats_log_path = start_nats(args, run_dir, nats_url)
        ok = wait_for_log_line(nats_log_path, "Listening for client connections", 20)
        if not ok:
            terminate_proc(nats_proc)
            if nats_log_file:
                nats_log_file.close()
            raise SystemExit(f"Failed to start nats-server. See {nats_log_path}")
        print(f"[global] nats ready ({nats_url})")

    rows = []
    try:
        for threads in thread_values:
            for batch_size in batches:
                for run_idx in range(1, args.runs + 1):
                    print(
                        f"Running threads={threads if threads is not None else 'yaml'} batch={batch_size} run={run_idx} ...")
                    row = run_one(args, os.environ, run_dir, base_config, batch_size, threads, run_idx)
                    rows.append(row)
                    print(
                        f"  done: stage_fps={fmt(row['stage_fps'])} "
                        f"overhead_pct={fmt(row['drava_overhead_pct'])} "
                        f"gpu_j_per_frame={fmt(row['gpu_energy_j_per_frame'], '{:.4f}')}"
                    )
        print_table(rows)
        print_aggregate_table(rows)
        write_summary_csv(run_dir / "summary.csv", rows)
        print(f"\nLogs and summary written to: {run_dir}")
    except BaseException:
        print(f"\nLogs written to: {run_dir}")
        raise
    finally:
        if nats_proc is not None:
            print("[global] stopping nats-server")
            terminate_proc(nats_proc)
        if nats_log_file is not None:
            nats_log_file.close()


if __name__ == "__main__":
    main()
