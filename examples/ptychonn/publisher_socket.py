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
import numpy as np
import os
import struct

FIFO_PATH = "/tmp/drava_in"

DATA_DIR = "PtychoNN_data_partial"

# target framerate from env:
#   unset or <= 0 => max speed (no pacing)
#   e.g. export DRAVA_PUBLISH_RATE_HZ=1000
RATE_HZ = float(os.getenv("DRAVA_PUBLISH_RATE_HZ", "1000"))
LOG_EVERY = 256


def main():
    if not os.path.exists(FIFO_PATH):
        raise RuntimeError(
            f"FIFO {FIFO_PATH} does not exist. "
            f"Create it (mkfifo {FIFO_PATH}) and start socat/Drava socket transport first."
        )

    X_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")  # (N,64,64,1)
    n_frames = X_test.shape[0]
    print("X_test shape:", X_test.shape)

    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    next_t = (t0 + period) if pacing else None

    print(f"Opening FIFO {FIFO_PATH} for writing...")
    with open(FIFO_PATH, "wb") as f:
        for idx in range(n_frames):
            frame = X_test[idx]  # (64,64,1)
            payload = frame.tobytes(order="C")
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            f.flush()

            win_count += 1
            if idx == 0:
                print(f"First frame sent at:{t0}")

            if (idx + 1) % LOG_EVERY == 0 or idx == n_frames - 1:
                now = time.perf_counter()
                dt_total = now - t0
                dt_win = now - win_t0

                avg_fps = (idx + 1) / dt_total if dt_total > 0 else float("inf")
                win_fps = win_count / dt_win if dt_win > 0 else float("inf")

                print(
                    f"Published idx={idx}/{n_frames} "
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

    t_end = time.perf_counter()
    total_dt = t_end - t0
    print(
        f"Done: published {n_frames} frames in {total_dt:.3f}s "
        f"(avg_fps={n_frames/total_dt:.2f}) "
        f"Last frame sent at: {t_end}"
    )


if __name__ == "__main__":
    main()
