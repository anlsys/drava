"""
Frame-by-frame publisher for Drava socket transport (FIFO -> socat -> UNIX socket).
Wire format per frame: [4-byte big-endian payload length][raw frame bytes].
"""

import os
import struct
import time

from publisher_util import (
    load_dataset_payloads,
    load_publish_config,
    write_publisher_metrics,
)

FIFO_PATH = os.getenv("DRAVA_OUTPUT_FIFO_PATH", "/tmp/drava_in")
RATE_HZ, TARGET_FRAMES = load_publish_config()
LOG_EVERY = 128
EOS_PREFIX = b"DRAVA_EOS:"


def main():
    if not os.path.exists(FIFO_PATH):
        raise RuntimeError(
            f"FIFO {FIFO_PATH} does not exist. "
            f"Create it (mkfifo {FIFO_PATH}) and start socat/Drava socket transport first."
        )

    payloads = load_dataset_payloads()
    n_payloads = len(payloads)
    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0
    next_t = (t0 + period) if pacing else None

    with open(FIFO_PATH, "wb") as f:
        sent_count = 0
        while sent_count < TARGET_FRAMES:
            payload = payloads[sent_count % n_payloads]
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            f.flush()

            sent_count += 1
            win_count += 1
            if sent_count == 1:
                print(f"First frame sent at: {t0}")

            if sent_count % LOG_EVERY == 0:
                now = time.perf_counter()
                dt_total = now - t0
                dt_win = now - win_t0
                avg_fps = sent_count / dt_total if dt_total > 0 else float("inf")
                win_fps = win_count / dt_win if dt_win > 0 else float("inf")
                print(
                    f"Published count={sent_count} "
                    f"win_fps={win_fps:.2f} avg_fps={avg_fps:.2f}"
                )
                win_t0 = now
                win_count = 0

            if pacing:
                sleep_s = next_t - time.perf_counter()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                next_t += period

        eos_payload = EOS_PREFIX + str(sent_count).encode("ascii")
        f.write(struct.pack("!I", len(eos_payload)))
        f.write(eos_payload)
        f.flush()

    t_end = time.perf_counter()
    total_dt = t_end - t0
    avg_fps = sent_count / total_dt if total_dt > 0 else 0.0
    print(
        f"Done: published {sent_count} frames in {total_dt:.3f}s "
        f"(avg_fps={avg_fps:.2f})"
    )
    write_publisher_metrics(sent_count, total_dt, avg_fps)


if __name__ == "__main__":
    main()
