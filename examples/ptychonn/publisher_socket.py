"""
Frame-by-frame publisher for Drava socket transport (FIFO -> socat -> UNIX socket).

Prereqs (example):
  mkfifo /tmp/drava_in
  socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork

Drava socket transport:
  export DRAVA_TRANSPORT=socket
"""
import json
import base64
import time
import numpy as np
import os

FIFO_PATH = "/tmp/drava_in"

PATCH_SIDE = 64
DATA_DIR = "PtychoNN_data_partial"

# target framerate: set to None or 0 for max speed
RATE_HZ = 1000.0
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

    job_id = int(time.time_ns())

    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    next_t = (t0 + period) if pacing else None

    print(f"Opening FIFO {FIFO_PATH} for writing...")
    with open(FIFO_PATH, "w") as f:
        for idx in range(n_frames):
            frame = X_test[idx]  # (64,64,1)

            payload = {
                "kind": "ptychonn_frame",
                "job_id": job_id,
                "frame_id": int(time.time_ns()),
                "idx": idx,
                "rows": 1,
                "patch_side": PATCH_SIDE,
                "dtype": "float32",
                "order": "C",
                "data_b64": base64.b64encode(frame.tobytes(order="C")).decode(),
                "n_total": n_frames,
            }

            f.write(json.dumps(payload) + "\n")
            f.flush()

            win_count += 1

            if (idx + 1) % LOG_EVERY == 0 or idx == n_frames - 1:
                now = time.perf_counter()
                dt_total = now - t0
                dt_win = now - win_t0

                avg_fps = (idx + 1) / dt_total if dt_total > 0 else float("inf")
                win_fps = win_count / dt_win if dt_win > 0 else float("inf")

                print(
                    f"Sent idx={idx}/{n_frames-1} "
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

    total_dt = time.perf_counter() - t0
    print(
        f"Done: sent {n_frames} frames in {total_dt:.3f}s "
        f"(avg_fps={n_frames/total_dt:.2f})"
    )


if __name__ == "__main__":
    main()
