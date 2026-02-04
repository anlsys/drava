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


def main():
    if not os.path.exists(FIFO_PATH):
        raise RuntimeError(
            f"FIFO {FIFO_PATH} does not exist. "
            f"Create it (mkfifo {FIFO_PATH}) and start socat/Drava socket transport first."
        )

    # Load input frames (N,64,64,1)
    X_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")
    n_frames = X_test.shape[0]
    print("X_test shape:", X_test.shape)

    job_id = int(time.time_ns())

    print(f"Opening FIFO {FIFO_PATH} for writing...")
    # Text mode because Drava expects newline-delimited JSON strings
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

            if idx % 256 == 0 or idx == n_frames - 1:
                print(f"Sent frame idx={idx}/{n_frames-1}")
    print("All frames sent.")


if __name__ == "__main__":
    main()
