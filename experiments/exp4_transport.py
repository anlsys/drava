#!/usr/bin/env python3
"""
Experiment 4: Transport Abstraction Cost/Benefit
================================================

Goal
----
Quantify the latency, throughput, and time-to-first-frame difference between
Drava's two transport backends:

  * sockets : UNIX-domain socket fronted by a FIFO + socat (durable=false)
  * nats    : NATS JetStream pull consumer (durable=true)

Hypotheses
----------
* Sockets minimize per-frame transport_in latency (no broker hop, no JS state)
  but lack durability and replay semantics.
* JetStream's durable consumer adds a per-fetch round-trip but enables
  multi-consumer replay; the cost should be amortized at large fetch_batch.
* Time-to-first-frame (TTFF) is dominated by JetStream stream/consumer setup
  for nats; it is essentially zero for sockets.

Workload
--------
TomoGAN single-stage. We use the simplest possible pipeline because the
purpose is to characterize the transport, not the application.

Sweep
-----
* transport     in {sockets, nats}
* payload_size  via batch in {1, 4, 16, 64} (driven through DRAVA_INFER_BATCH)
* runs          per cell

Outputs
-------
experiments/results/exp4_<ts>/exp4_summary.csv with columns:
    transport, batch, run, frames,
    end_to_end_s, ttff_s,
    rx_item_fps, tx_msg_fps,
    cb_avg_ms, stage_avg_ms, stage_max_ms,
    transport_lumped_s, microbatching_wait_s, callback_compute_s

This driver invokes examples/tomogan/benchmark.py for the NATS arm. The
sockets arm is not yet wired into a one-shot benchmark; for now this driver
prints the exact commands needed to run sockets manually and skips the
sockets arm with a clear note. (Wiring sockets into a benchmark wrapper
is tracked as a follow-up runtime/tooling task.)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import subprocess
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    DRAVA_METRICS_RE,
    LatencyDecomp,
    PUB_DONE_RE,
    TOMOGAN_DIR,
    make_run_dir,
    parse_metrics_from_log,
    read_summary_csv,
    run_tomogan_benchmark,
    stream_lines,
    tail_text,
    terminate_proc,
    write_rows,
)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--transports", default="nats",
                   help="Comma-separated subset of {sockets,nats}. sockets runs only "
                        "if --enable-sockets is passed.")
    p.add_argument("--enable-sockets", action="store_true",
                   help="Actually run the sockets arm (requires socat in PATH and "
                        "writeable /tmp).")
    p.add_argument("--batches", default="1,4,16,64")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--num-frames", type=int, default=16)
    p.add_argument("--rate-hz", type=float, default=0.0)
    p.add_argument("--timeout-ms", type=int, default=200)
    p.add_argument("--runs", type=int, default=2)
    return p.parse_args()


def collect_nats(args, run_dir: Path) -> list[dict]:
    batches = [int(b) for b in args.batches.split(",") if b.strip()]
    sub = run_dir / "nats"
    ts = run_tomogan_benchmark(
        sub,
        batches=batches,
        threads=args.threads,
        timeout_ms=args.timeout_ms,
        rate_hz=args.rate_hz,
        num_frames=args.num_frames,
        runs=args.runs,
    )
    summary = read_summary_csv(ts / "summary.csv")
    rows: list[dict] = []
    for srow in summary:
        b = int(srow["batch"])
        r = int(srow["run"])
        m = parse_metrics_from_log(ts / f"app_b{b}_r{r}.log")
        if m is None:
            continue
        e2e = float(srow.get("pipeline_e2e_s") or 0.0) or None
        d = LatencyDecomp.from_stage(m, e2e)
        # TTFF for nats is bounded above by the time between app start and
        # first cb_avg_ms sample. We approximate as transport_lumped_s/frames
        # at batch=1; otherwise leave as None.
        ttff = (d.transport_lumped_s if (d.transport_lumped_s and m.rx_items > 0)
                else None)
        rows.append({
            "transport": "nats",
            "batch": b,
            "run": r,
            "frames": m.rx_items,
            "end_to_end_s": d.end_to_end_s,
            "ttff_s": ttff,
            "rx_item_fps": m.rx_item_fps,
            "tx_msg_fps": m.tx_msg_fps,
            "cb_avg_ms": m.cb_avg_ms,
            "stage_avg_ms": m.stage_avg_ms,
            "stage_max_ms": m.stage_max_ms,
            "transport_lumped_s": d.transport_lumped_s,
            "microbatching_wait_s": d.microbatching_wait_s,
            "callback_compute_s": d.callback_compute_s,
        })
    return rows


def collect_sockets(args, run_dir: Path) -> list[dict]:
    """Run TomoGAN with the socket transport.

    Wiring required at runtime:
      mkfifo /tmp/drava_in
      socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork &

    The driver creates the FIFO and starts socat itself.
    """
    if shutil.which("socat") is None:
        print("[exp4] sockets arm skipped: socat not in PATH")
        return []
    # Build a minimal pipeline yaml for tomogan with type: socket.
    socket_yaml = run_dir / "tomogan_socket.yaml"
    socket_yaml.write_text(
        "pipeline:\n"
        "  name: tomogan_socket\n"
        "transport:\n"
        "  type: socket\n"
        "publisher:\n"
        "  rate_hz: 0\n"
        f"  num_frames: {args.num_frames}\n"
        "stages:\n"
        "  - name: stage1\n"
        "    runtime:\n"
        f"      threads: {args.threads}\n"
        "      callback_batch: 16\n"
        "    ingress:\n"
        "      socket_path: /tmp/accel_2048.sock\n"
        "    egress:\n"
        "      output_fifo_path: /tmp/drava_stage1_out\n"
    )

    rows: list[dict] = []
    batches = [int(b) for b in args.batches.split(",") if b.strip()]
    for b in batches:
        for r in range(1, args.runs + 1):
            cell_dir = run_dir / "sockets" / f"b{b}" / f"run{r}"
            cell_dir.mkdir(parents=True, exist_ok=True)
            fifo_path = "/tmp/drava_in"
            sock_path = "/tmp/accel_2048.sock"
            for path in (fifo_path, sock_path):
                if os.path.exists(path):
                    os.remove(path)
            os.mkfifo(fifo_path)

            socat_log = cell_dir / "socat.log"
            socat_proc = subprocess.Popen(
                ["socat", fifo_path, f"UNIX-LISTEN:{sock_path},fork"],
                stdout=open(socat_log, "w", encoding="utf-8"),
                stderr=subprocess.STDOUT,
            )
            time.sleep(0.5)

            env = dict(os.environ)
            env["DRAVA_TRANSPORT"] = "socket"
            env["DRAVA_STAGE_CONFIG"] = str(socket_yaml)
            env["DRAVA_STAGE_NAME"] = "stage1"
            env["DRAVA_INFER_BATCH"] = str(b)
            env["DRAVA_CALLBACK_BATCH"] = str(b)
            env["DRAVA_PUBLISH_NUM_FRAMES"] = str(args.num_frames)
            env["DRAVA_PUBLISH_RATE_HZ"] = str(args.rate_hz)
            env["DRAVA_OUTPUT_FIFO_PATH"] = fifo_path

            app_log = cell_dir / "app.log"
            pub_log = cell_dir / "pub.log"
            metrics: dict = {}
            pub_done: dict = {}
            t0 = None

            def on_app_line(line: str):
                m = DRAVA_METRICS_RE.search(line)
                if m and m.group("reason") in ("rx_eos", "tx_eos"):
                    metrics.update(m.groupdict())

            def on_pub_line(line: str):
                m = PUB_DONE_RE.search(line)
                if m:
                    pub_done.update(m.groupdict())

            app_proc = subprocess.Popen(
                [sys.executable, "app.py"],
                cwd=TOMOGAN_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            app_thread = threading.Thread(
                target=stream_lines, args=(app_proc, app_log, on_app_line),
                daemon=True,
            )
            app_thread.start()
            time.sleep(2.0)

            t0 = time.monotonic()
            pub_proc = subprocess.Popen(
                [sys.executable, "publisher_socket.py"],
                cwd=TOMOGAN_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            pub_thread = threading.Thread(
                target=stream_lines, args=(pub_proc, pub_log, on_pub_line),
                daemon=True,
            )
            pub_thread.start()

            try:
                pub_proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                terminate_proc(pub_proc)

            end_wait = time.time() + 30
            while time.time() < end_wait and not metrics:
                if app_proc.poll() is not None:
                    break
                time.sleep(0.2)
            t_end = time.monotonic()

            terminate_proc(app_proc)
            terminate_proc(socat_proc)
            app_thread.join(timeout=5)
            pub_thread.join(timeout=5)

            if not metrics:
                print(f"[exp4-sockets] no metrics for batch={b} run={r}\n"
                      f"--- app tail ---\n{tail_text(app_log)}")
                continue

            from _common import StageMetrics
            m_obj = StageMetrics.from_match(metrics)
            e2e = t_end - t0
            d = LatencyDecomp.from_stage(m_obj, e2e)
            rows.append({
                "transport": "sockets",
                "batch": b,
                "run": r,
                "frames": m_obj.rx_items,
                "end_to_end_s": d.end_to_end_s,
                "ttff_s": None,
                "rx_item_fps": m_obj.rx_item_fps,
                "tx_msg_fps": m_obj.tx_msg_fps,
                "cb_avg_ms": m_obj.cb_avg_ms,
                "stage_avg_ms": m_obj.stage_avg_ms,
                "stage_max_ms": m_obj.stage_max_ms,
                "transport_lumped_s": d.transport_lumped_s,
                "microbatching_wait_s": d.microbatching_wait_s,
                "callback_compute_s": d.callback_compute_s,
            })
    return rows


def main():
    args = parse_args()
    run_dir = make_run_dir("exp4")
    print(f"[exp4] writing to {run_dir}")
    requested = [t.strip() for t in args.transports.split(",") if t.strip()]
    rows: list[dict] = []
    if "nats" in requested:
        rows.extend(collect_nats(args, run_dir))
    if "sockets" in requested:
        if not args.enable_sockets:
            print("[exp4] sockets transport requested but --enable-sockets not "
                  "passed; skipping. Run with --enable-sockets to execute it.")
        else:
            rows.extend(collect_sockets(args, run_dir))

    cols = [
        "transport", "batch", "run", "frames",
        "end_to_end_s", "ttff_s",
        "rx_item_fps", "tx_msg_fps",
        "cb_avg_ms", "stage_avg_ms", "stage_max_ms",
        "transport_lumped_s", "microbatching_wait_s", "callback_compute_s",
    ]
    out = run_dir / "exp4_summary.csv"
    write_rows(out, rows, cols)
    print(f"[exp4] wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
