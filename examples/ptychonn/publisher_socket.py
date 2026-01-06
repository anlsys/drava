#!/usr/bin/env python3
import json
import base64
import time
import numpy as np
import os

FIFO_PATH = "/tmp/drava_in"

PATCH_SIDE = 64
BATCH_SIZE = 32
DATA_DIR = "PtychoNN_data_partial"


def main():
    # Ensure FIFO exists
    if not os.path.exists(FIFO_PATH):
        raise RuntimeError(
            f"FIFO {FIFO_PATH} does not exist. "
            f"Start Drava with socket transport first."
        )

    # Load input patches
    X_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")  # (N,64,64,1)
    n_patches = X_test.shape[0]
    print("X_test shape:", X_test.shape)

    job_id = int(time.time_ns())

    print(f"Opening FIFO {FIFO_PATH} for writing...")
    with open(FIFO_PATH, "w") as f:
        for start in range(0, n_patches, BATCH_SIZE):
            end = min(start + BATCH_SIZE, n_patches)
            batch = X_test[start:end]  # (B,64,64,1)
            B = batch.shape[0]
            if B == 0:
                break

            payload = {
                "kind": "ptychonn_batch",
                "job_id": job_id,
                "frame_id": int(time.time_ns()),
                "start": start,
                "end": end,
                "rows": B,
                "patch_side": PATCH_SIDE,
                "dtype": "float32",
                "order": "C",
                "data_b64": base64.b64encode(batch.tobytes(order="C")).decode(),
                "n_total": n_patches,
            }

            msg = json.dumps(payload) + "\n"
            f.write(msg)
            f.flush()

            print(f"Sent batch [{start}:{end}]")

            # Optional small sleep to make logs readable
            # time.sleep(0.01)

    print("All batches sent.")


if __name__ == "__main__":
    main()
