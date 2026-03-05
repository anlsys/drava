"""
Frame-by-frame publisher for Drava socket transport (FIFO -> socat -> UNIX socket).
Wire format per frame: [4-byte big-endian payload length][raw frame bytes].

Prereqs (example):
  mkfifo /tmp/drava_in
  socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork

Drava socket transport:
  export DRAVA_TRANSPORT=socket
"""
import time
import os
import struct
from publisher_util import (
    compute_square_completion,
    load_publish_config,
    make_payload_generator,
)

FIFO_PATH = "/tmp/drava_in"

# target framerate from env:
#   unset or <= 0 => max speed (no pacing)
#   e.g. export DRAVA_PUBLISH_RATE_HZ=1000
RATE_HZ, SYNTHETIC_MODE, RUN_SECONDS = load_publish_config()
LOG_EVERY = 256
EOS_PREFIX = b"DRAVA_EOS:"


def main():
    if not os.path.exists(FIFO_PATH):
        raise RuntimeError(
            f"FIFO {FIFO_PATH} does not exist. "
            f"Create it (mkfifo {FIFO_PATH}) and start socat/Drava socket transport first."
        )

    next_payload = make_payload_generator(SYNTHETIC_MODE)
    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    next_t = (t0 + period) if pacing else None

    print(f"Opening FIFO {FIFO_PATH} for writing...")
    with open(FIFO_PATH, "wb") as f:
        sent_count = 0
        while True:
            elapsed = time.perf_counter() - t0
            if elapsed >= RUN_SECONDS:
                break
            source_idx = sent_count
            payload = next_payload(source_idx)
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            f.flush()

            sent_count += 1
            win_count += 1
            if sent_count == 1:
                print(f"First frame sent at:{t0}")

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

            # Pace only if enabled
            if pacing:
                sleep_s = next_t - time.perf_counter()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                next_t += period

        n_raw = sent_count
        side, n_square, extra = compute_square_completion(n_raw)
        print(
            f"Square completion: n_raw={n_raw} side={side} n_square={n_square} extra={extra}"
        )
        for _ in range(extra):
            source_idx = sent_count
            payload = next_payload(source_idx)
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            f.flush()
            sent_count += 1
            win_count += 1

        # End-of-stream marker with sent frame count
        eos_payload = EOS_PREFIX + str(n_square).encode("ascii")
        f.write(struct.pack("!I", len(eos_payload)))
        f.write(eos_payload)
        f.flush()

    t_end = time.perf_counter()
    total_dt = t_end - t0
    print(
        f"Done: published {sent_count} frames in {total_dt:.3f}s "
        f"(avg_fps={sent_count / total_dt:.2f}) "
        f"Last frame sent at: {t_end}"
    )


if __name__ == "__main__":
    main()
