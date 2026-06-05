#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

from pva_records import (
    FRAME_CHANNEL,
    FRAME_SHAPE,
    make_eos_frame_object,
    make_frame_object,
    make_initial_frame_object,
)

SYNTHETIC_SEED = 56465
SYNTHETIC_POOL_SIZE = 3600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish PtychoNN-sized frames over a pvaPy PVA channel."
    )
    parser.add_argument("--channel", default=FRAME_CHANNEL)
    parser.add_argument("--data-dir", default=os.getenv("PTYCHONN_DATA_DIR", "../PtychoNN_data_partial"))
    parser.add_argument("--synthetic", action="store_true", help="Use cached synthetic frames.")
    parser.add_argument("--num-frames", type=int, default=int(os.getenv("PVAPY_PUBLISH_NUM_FRAMES", "3600")))
    parser.add_argument("--rate-hz", type=float, default=float(os.getenv("PVAPY_PUBLISH_RATE_HZ", "0")))
    parser.add_argument("--startup-sleep-s", type=float, default=2.0)
    parser.add_argument("--control-file", default="", help="Wait for this file before publishing frames.")
    parser.add_argument("--log-every", type=int, default=1024)
    return parser.parse_args()


def make_payload_generator(data_dir: Path, synthetic: bool):
    if synthetic:
        rng = np.random.default_rng(SYNTHETIC_SEED)
        frames = rng.random((SYNTHETIC_POOL_SIZE, *FRAME_SHAPE), dtype=np.float32)
        payloads = [frame.tobytes(order="C") for frame in frames]
    else:
        x_test = np.load(data_dir / "X_test.npy").astype("float32")
        payloads = [frame.tobytes(order="C") for frame in x_test]

    if not payloads:
        raise RuntimeError("No payloads available to publish.")

    def next_payload(index: int) -> bytes:
        return payloads[index % len(payloads)]

    return next_payload


def wait_for_start(control_file: str, startup_sleep_s: float) -> None:
    if control_file:
        path = Path(control_file)
        print(f"[pvapy-publisher] waiting for control file: {path}", flush=True)
        while not path.exists():
            time.sleep(0.05)
        return
    if startup_sleep_s > 0:
        print(f"[pvapy-publisher] startup sleep: {startup_sleep_s:.3f}s", flush=True)
        time.sleep(startup_sleep_s)


def main() -> int:
    args = parse_args()
    if args.num_frames <= 0:
        raise SystemExit("--num-frames must be > 0")

    try:
        import pvaccess
    except ImportError as exc:
        raise SystemExit("Missing pvaPy module. Install with `pip install pvapy`.") from exc

    data_dir = Path(args.data_dir).resolve()
    next_payload = make_payload_generator(data_dir, args.synthetic)
    pv = make_initial_frame_object(pvaccess)
    server = pvaccess.PvaServer(args.channel, pv)
    print(f"[pvapy-publisher] PVA input channel ready: {args.channel}", flush=True)

    wait_for_start(args.control_file, args.startup_sleep_s)

    pacing = args.rate_hz > 0
    period = 1.0 / args.rate_hz if pacing else 0.0
    next_t = time.perf_counter() + period
    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    try:
        for frame_id in range(args.num_frames):
            payload = next_payload(frame_id)
            server.update(make_frame_object(pvaccess, frame_id, args.num_frames, payload))
            if frame_id == 0:
                print(f"First frame sent at:{t0}", flush=True)

            win_count += 1
            sent = frame_id + 1
            if args.log_every > 0 and sent % args.log_every == 0:
                now = time.perf_counter()
                dt_total = now - t0
                dt_win = now - win_t0
                print(
                    f"Published count={sent} win_fps={win_count / dt_win:.2f} "
                    f"avg_fps={sent / dt_total:.2f}",
                    flush=True,
                )
                win_t0 = now
                win_count = 0

            if pacing:
                sleep_s = next_t - time.perf_counter()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                next_t += period

        server.update(make_eos_frame_object(pvaccess, args.num_frames, args.num_frames))
        t_end = time.perf_counter()
        total_s = t_end - t0
        print(
            f"Done: published {args.num_frames} frames in {total_s:.3f}s "
            f"(avg_fps={args.num_frames / total_s:.2f}) Last frame sent at: {t_end}",
            flush=True,
        )
        time.sleep(0.5)
    finally:
        server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
