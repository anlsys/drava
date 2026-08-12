#!/usr/bin/env python3
import argparse
import datetime as dt
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

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
    p.add_argument("--nats-max-payload", default="8MB",
                   help="max_payload for the auto-started nats-server (TomoGAN frames are 4 MB).")
    p.add_argument("--stage-config", default="pipeline.yaml", help="Base stage config YAML path.")
    p.add_argument("--out-dir", default="bench_logs", help="Output directory under examples/tomogan.")
    p.add_argument("--app-timeout-s", type=float, default=None, help="Max wait for app metrics after publisher exits.")
    p.add_argument("--gpu-sample-interval-s", type=float, default=0.2, help="nvidia-smi sampling interval.")
    p.add_argument("--no-gpu-energy", action="store_true", help="Disable nvidia-smi power sampling.")
    p.add_argument("--rapl-glob", default="/sys/class/powercap/intel-rapl:*/energy_uj",
                   help="RAPL energy_uj glob. Use '' to disable RAPL CPU/package energy sampling.")
    p.add_argument("--cpu-energy-source", choices=["auto", "perf", "rapl", "none"], default="auto",
                   help="CPU package energy source. 'perf' uses `perf stat -e power/energy-pkg/`, "
                        "'rapl' reads the powercap sysfs, 'auto' tries perf then falls back to RAPL, "
                        "'none' disables CPU energy.")
    p.add_argument("--perf-command", default="perf", help="perf executable used for CPU energy.")
    p.add_argument("--perf-energy-event", default="power/energy-pkg/",
                   help="perf event(s) for CPU package energy (comma-separated for multi-socket).")
    p.add_argument("--perf-interval-ms", type=int, default=200,
                   help="perf stat interval (-I) in ms for the CPU power time-series.")
    p.add_argument("--save-power-trace", action="store_true",
                   help="Write per-run GPU/CPU power-vs-time traces to power_trace_*.csv.")
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
    # TomoGAN frames are 1024x1024 float32 = 4 MB, which exceeds NATS' default
    # 1 MB max_payload. Raise it when auto-starting nats-server so the default
    # launch path works without requiring an external --nats-config.
    cmd = [args.nats_command, "-js", "-a", host, "-p", port,
           "--max_payload", args.nats_max_payload]
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


def integrate_power_j(samples, start_t, end_t):
    window = [(t, p) for (t, p, _u, _m) in samples if start_t <= t <= end_t]
    if len(window) < 2:
        return None
    joules = 0.0
    for (t0, p0), (t1, p1) in zip(window, window[1:]):
        joules += ((p0 + p1) * 0.5) * (t1 - t0)
    return joules


def average_window(samples, start_t, end_t, index):
    values = [sample[index] for sample in samples if start_t <= sample[0] <= end_t]
    return sum(values) / len(values) if values else None


def read_rapl_domains(pattern: str):
    if not pattern:
        return {}
    domains = {}
    for energy_path in Path("/").glob(pattern.lstrip("/")):
        try:
            base = energy_path.parent
            max_path = base / "max_energy_range_uj"
            name_path = base / "name"
            name = name_path.read_text(encoding="utf-8").strip() if name_path.exists() else base.name
            domains[str(energy_path)] = (
                name,
                int(energy_path.read_text(encoding="utf-8").strip()),
                int(max_path.read_text(encoding="utf-8").strip()) if max_path.exists() else None,
            )
        except Exception:
            pass
    return domains


def perf_energy_available(perf_command: str, event: str) -> bool:
    """Return True if `perf stat` can read the CPU package energy event."""
    try:
        proc = subprocess.run(
            [perf_command, "stat", "-e", event, "--", "sleep", "0.2"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except Exception:
        return False
    err = proc.stderr or ""
    # perf prints "<not supported>" / "<not counted>" when the event is unusable,
    # and reports "Joules" on success.
    if "<not supported>" in err or "<not counted>" in err:
        return False
    return "Joules" in err


class PerfEnergySampler:
    """Measure CPU package energy over a window with `perf stat`.

    Runs `perf stat -e power/energy-pkg/ -I <interval_ms> -- sleep <big>` in the
    background for the duration of the measurement window, then interrupts it and
    parses both (i) the total Joules and (ii) an interval time-series that is
    converted into a CPU power (W) trace for line charts. This mirrors the
    perf-based CPU energy approach used in the instruction-count energy sweeps and
    works on JLSE AMD EPYC nodes where the RAPL powercap sysfs is not readable.
    """

    def __init__(self, perf_command: str, event: str, interval_ms: int = 200,
                 max_window_s: float = 3600.0):
        self.perf_command = perf_command
        self.event = event
        self.interval_ms = int(interval_ms)
        self.max_window_s = max_window_s
        self.proc: subprocess.Popen | None = None
        self.stderr_text: str = ""
        # Power time-series as (monotonic_time_s, power_w) captured at stop().
        self.power_samples: list[tuple[float, float]] = []
        self._t0: float | None = None

    def start(self) -> bool:
        events = []
        for ev in self.event.split(","):
            ev = ev.strip()
            if ev:
                events += ["-e", ev]
        # Machine-readable CSV output (-x,) is flushed reliably per interval and
        # is locale-independent, unlike the human-readable table. Interval lines:
        #   <elapsed_s>,<counter>,<unit>,<event>,...  e.g. "0.200,12.50,Joules,power/energy-pkg/,..."
        cmd = [self.perf_command, "stat", "-x", ",", *events, "-I", str(self.interval_ms),
               "--", "sleep", str(self.max_window_s)]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
        except Exception:
            self.proc = None
            return False
        self._t0 = time.monotonic()
        return True

    def stop(self, debug_path: "Path | None" = None) -> float | None:
        if self.proc is None:
            return None
        try:
            # SIGINT makes perf stop counting and flush its final report.
            self.proc.send_signal(signal.SIGINT)
            _out, err = self.proc.communicate(timeout=15)
        except Exception:
            try:
                self.proc.terminate()
                _out, err = self.proc.communicate(timeout=5)
            except Exception:
                self.proc.kill()
                err = ""
        self.stderr_text = err or ""
        if debug_path is not None:
            try:
                debug_path.write_text(self.stderr_text, encoding="utf-8")
            except Exception:
                pass
        self.power_samples = self._parse_interval_power(self.stderr_text, self._t0)
        joules = self._parse_joules(self.stderr_text)
        if joules is None and self.stderr_text.strip():
            tail = "\n".join(self.stderr_text.strip().splitlines()[-5:])
            print(f"[perf] WARNING: could not parse CPU energy from perf output. "
                  f"Last lines:\n{tail}", flush=True)
        return joules

    @staticmethod
    def _parse_joules(text: str) -> float | None:
        # Sum the Joules value from every parsed row (CSV or human-readable).
        # With -I, each interval contributes one row, so the sum is total energy.
        total = None
        for _elapsed, joules in PerfEnergySampler._iter_joules_rows(text):
            total = (total or 0.0) + joules
        return total

    def _parse_interval_power(self, text: str, t0: float | None):
        interval_s = self.interval_ms / 1000.0
        base = t0 if t0 is not None else 0.0
        out: list[tuple[float, float]] = []
        for elapsed, joules in PerfEnergySampler._iter_joules_rows(text):
            power_w = joules / interval_s if interval_s > 0 else 0.0
            ts = base + elapsed if elapsed is not None else base
            out.append((ts, power_w))
        return out

    @staticmethod
    def _iter_joules_rows(text: str):
        """Yield (elapsed_s|None, joules) for each energy line.

        Handles both `perf stat -x,` CSV rows and the human-readable table.
        CSV interval row: "0.200122853,,12.50,Joules,power/energy-pkg/,..."
        CSV summary row:  "12.50,Joules,power/energy-pkg/,..."
        Text interval:    "     0.200122853     12.50 Joules power/energy-pkg/"
        Text summary:     "            12.50 Joules power/energy-pkg/"
        """
        for line in text.splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "Joules" not in raw:
                continue
            if "," in raw:
                fields = [f.strip() for f in raw.split(",")]
                # Find the "Joules" unit field; the counter value is the nearest
                # non-empty numeric field before it (perf -x, emits empty fields,
                # e.g. "<elapsed>,,<value>,,Joules,<event>,...").
                try:
                    u = fields.index("Joules")
                except ValueError:
                    continue
                joules = None
                value_idx = None
                for j in range(u - 1, -1, -1):
                    v = PerfEnergySampler._maybe_float(fields[j])
                    if v is not None:
                        joules = v
                        value_idx = j
                        break
                if joules is None:
                    continue
                # An elapsed-time field precedes the value only in interval rows.
                elapsed = None
                if value_idx is not None and value_idx >= 1:
                    elapsed = PerfEnergySampler._maybe_float(fields[0])
                    if elapsed == joules:
                        elapsed = None
                yield elapsed, joules
            else:
                tokens = raw.split()
                try:
                    u = tokens.index("Joules")
                except ValueError:
                    continue
                if u < 1:
                    continue
                joules = PerfEnergySampler._maybe_float(tokens[u - 1].replace(",", ""))
                elapsed = PerfEnergySampler._maybe_float(tokens[0]) if u >= 2 else None
                if joules is not None:
                    yield elapsed, joules

    @staticmethod
    def _maybe_float(token: str) -> float | None:
        try:
            return float(token)
        except (ValueError, TypeError):
            return None


def rapl_delta_j(before: dict, after: dict):
    total_uj = 0
    matched = False
    for path, (_name, start, max_range) in before.items():
        if path not in after:
            continue
        matched = True
        end = after[path][1]
        if end >= start:
            total_uj += end - start
        elif max_range is not None:
            total_uj += (max_range - start) + end
    return total_uj / 1_000_000.0 if matched else None


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
    app_ready = threading.Event()
    app_metrics = {}
    pub_done = {}
    marks = {"publish_start": None, "metrics": None}

    def on_app_line(line: str):
        if "JetStream ready:" in line:
            app_ready.set()
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
    if not args.no_gpu_energy:
        gpu_thread = threading.Thread(
            target=gpu_power_sampler,
            args=(gpu_stop, gpu_samples, args.gpu_sample_interval_s),
            daemon=True,
        )
        gpu_thread.start()

    cpu_source = getattr(args, "_cpu_source", "none")
    perf_sampler = None
    if cpu_source == "perf":
        perf_sampler = PerfEnergySampler(
            args.perf_command, args.perf_energy_event, interval_ms=args.perf_interval_ms,
        )
        if not perf_sampler.start():
            perf_sampler = None
    rapl_before = read_rapl_domains(args.rapl_glob) if cpu_source == "rapl" else {}
    print(f"[batch={batch_size} run={run_idx}] starting publisher_jetstream.py")
    marks["publish_start"] = time.monotonic()
    pub_proc = subprocess.Popen(
        [args.python, "publisher_jetstream.py"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pub_thread = threading.Thread(target=stream_lines, args=(pub_proc, pub_log, on_pub_line), daemon=True)
    pub_thread.start()

    expected_frames = configured_num_frames if configured_num_frames > 0 else 16
    pub_timeout_s = max(180, int(max(1, expected_frames) / 1000) + 180)
    pub_proc.wait(timeout=pub_timeout_s)
    pub_thread.join(timeout=5)

    end_wait = time.time() + effective_app_timeout_s
    while time.time() < end_wait and not app_metrics:
        if app_proc.poll() is not None:
            break
        time.sleep(0.2)
    rapl_after = read_rapl_domains(args.rapl_glob) if cpu_source == "rapl" else {}
    perf_debug_path = run_dir / f"perf_b{batch_size}_r{run_idx}.txt"
    perf_cpu_energy_j = perf_sampler.stop(perf_debug_path) if perf_sampler is not None else None

    gpu_stop.set()
    if gpu_thread is not None:
        gpu_thread.join(timeout=2)
    terminate_proc(app_proc)
    app_thread.join(timeout=5)

    if not pub_done:
        raise RuntimeError(f"publisher final line not found\n--- pub tail ---\n{tail_text(pub_log)}")
    if not app_metrics:
        raise RuntimeError(f"drava metrics line not found\n--- app tail ---\n{tail_text(app_log)}")

    publisher_frames = int(pub_done["frames"])
    stage_frames = int(app_metrics["rx_items"])
    if publisher_frames != stage_frames:
        raise RuntimeError(f"frame mismatch: publisher={publisher_frames} stage1={stage_frames}")

    start_t = marks["publish_start"]
    end_t = marks["metrics"] or time.monotonic()
    gpu_energy_j = integrate_power_j(gpu_samples, start_t, end_t) if gpu_samples else None
    if perf_cpu_energy_j is not None:
        cpu_energy_j = perf_cpu_energy_j
    else:
        cpu_energy_j = rapl_delta_j(rapl_before, rapl_after)

    if args.save_power_trace:
        cpu_trace = perf_sampler.power_samples if perf_sampler is not None else []
        write_power_trace(
            run_dir / f"power_trace_b{batch_size}_r{run_idx}.csv",
            gpu_samples, cpu_trace, start_t, end_t,
        )

    total_energy_j = None
    if gpu_energy_j is not None or cpu_energy_j is not None:
        total_energy_j = (gpu_energy_j or 0.0) + (cpu_energy_j or 0.0)
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
        "publisher_time_s": float(pub_done["time"]),
        "publisher_avg_fps": float(pub_done["fps"]),
        "stage_time_s": stage_time_s,
        "stage_fps": float(app_metrics["stage_total_fps"]),
        "cb_avg_ms": float(app_metrics["cb_avg_ms"]),
        "pipeline_e2e_s": e2e_s,
        "drava_overhead_s": drava_overhead_s,
        "drava_overhead_pct": drava_overhead_pct,
        "gpu_avg_power_w": average_window(gpu_samples, start_t, end_t, 1),
        "gpu_avg_util_pct": average_window(gpu_samples, start_t, end_t, 2),
        "gpu_avg_mem_mib": average_window(gpu_samples, start_t, end_t, 3),
        "gpu_energy_j": gpu_energy_j,
        "gpu_energy_j_per_frame": gpu_energy_j / publisher_frames if gpu_energy_j is not None else None,
        "cpu_energy_source": cpu_source,
        "cpu_energy_j": cpu_energy_j,
        "cpu_energy_j_per_frame": cpu_energy_j / publisher_frames if cpu_energy_j is not None else None,
        # Backward-compatible alias for existing scripts/logs.
        "cpu_rapl_energy_j": cpu_energy_j,
        "total_energy_j": total_energy_j,
        "total_energy_j_per_frame": total_energy_j / publisher_frames if total_energy_j is not None else None,
    }


def print_table(rows):
    print("")
    print(
        "| Batch | Threads | Frames | Stage Time (s) | Stage FPS | E2E (s) | "
        "Overhead (s) | Overhead (%) | GPU Power (W) | GPU Energy (J) | GPU J/frame | "
        "CPU src | CPU (J) | CPU J/frame | Total J/frame |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['batch']} | {r['threads']} | {r['frames']} | {fmt(r['stage_time_s'])} | "
            f"{fmt(r['stage_fps'])} | {fmt(r['pipeline_e2e_s'])} | "
            f"{fmt(r['drava_overhead_s'])} | {fmt(r['drava_overhead_pct'])} | "
            f"{fmt(r['gpu_avg_power_w'])} | {fmt(r['gpu_energy_j'])} | "
            f"{fmt(r['gpu_energy_j_per_frame'], '{:.4f}')} | {r.get('cpu_energy_source', 'n/a')} | "
            f"{fmt(r['cpu_energy_j'])} | {fmt(r.get('cpu_energy_j_per_frame'), '{:.4f}')} | "
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


def write_power_trace(path: Path, gpu_samples, cpu_samples, start_t, end_t):
    """Write a GPU/CPU power-vs-time trace for one run.

    Rows are (rel_time_s, source, power_w) so a plot can draw one line per
    source. Times are relative to the publisher-start marker.
    """
    rows = []
    for (t, power_w, _u, _m) in gpu_samples:
        if start_t <= t <= end_t:
            rows.append((t - start_t, "gpu", power_w))
    for (t, power_w) in cpu_samples:
        if start_t <= t <= end_t:
            rows.append((t - start_t, "cpu", power_w))
    rows.sort(key=lambda r: (r[0], r[1]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("rel_time_s,source,power_w\n")
        for rel_t, source, power_w in rows:
            f.write(f"{rel_t:.4f},{source},{power_w:.3f}\n")


def write_summary_csv(path: Path, rows):
    columns = [
        "batch", "run", "threads", "timeout_ms", "frames", "publisher_time_s",
        "publisher_avg_fps", "stage_time_s", "stage_fps", "cb_avg_ms", "pipeline_e2e_s",
        "drava_overhead_s", "drava_overhead_pct",
        "gpu_avg_power_w", "gpu_avg_util_pct", "gpu_avg_mem_mib", "gpu_energy_j",
        "gpu_energy_j_per_frame", "cpu_energy_source", "cpu_energy_j",
        "cpu_energy_j_per_frame", "cpu_rapl_energy_j", "total_energy_j",
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

    # Resolve the CPU package energy source once. On JLSE AMD EPYC nodes the RAPL
    # powercap sysfs is typically not readable, so `perf` is preferred.
    cpu_source = args.cpu_energy_source
    if cpu_source == "auto":
        if perf_energy_available(args.perf_command, args.perf_energy_event):
            cpu_source = "perf"
        elif args.rapl_glob and read_rapl_domains(args.rapl_glob):
            cpu_source = "rapl"
        else:
            cpu_source = "none"
    elif cpu_source == "perf":
        if not perf_energy_available(args.perf_command, args.perf_energy_event):
            print("[global] WARNING: perf CPU energy not available; CPU energy will be n/a. "
                  "Check `perf stat -e power/energy-pkg/ sleep 1` and perf_event_paranoid.", flush=True)
    args._cpu_source = cpu_source
    print(f"[global] CPU energy source: {cpu_source}")

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
                        f"gpu_j_per_frame={fmt(row['gpu_energy_j_per_frame'], '{:.4f}')} "
                        f"cpu_j={fmt(row['cpu_energy_j'])} "
                        f"cpu_j_per_frame={fmt(row.get('cpu_energy_j_per_frame'), '{:.4f}')} "
                        f"total_j_per_frame={fmt(row['total_energy_j_per_frame'], '{:.4f}')}"
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
