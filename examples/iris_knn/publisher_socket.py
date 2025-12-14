#!/usr/bin/env python3
import json
import base64
import time
import numpy as np
import pandas as pd

FIFO_PATH = "/tmp/drava_in"

def build_payload():
    feature_names = [
        'sepal length (cm)',
        'sepal width (cm)',
        'petal length (cm)',
        'petal width (cm)',
    ]
    arr = np.array([[5.1, 3.5, 1.4, 0.2]], dtype=np.float32)
    payload = {
        "rows": arr.shape[0],
        "cols": arr.shape[1],
        "dtype": "float32",
        "order": "C",
        "frame_id": int(time.time_ns()),
        "data_b64": base64.b64encode(arr.tobytes(order="C")).decode(),
        "feature_names": feature_names,
    }
    return payload

def main():
    print(f"Opening FIFO {FIFO_PATH} for writing.")
    print("Press Enter to send a frame. Press Ctrl+C to quit.\n")

    # Open FIFO once and keep it open
    with open(FIFO_PATH, "w") as f:
        while True:
            input("Press Enter to send frame...")
            payload = build_payload()
            msg = json.dumps(payload) + "\n"
            f.write(msg)
            f.flush()
            print(f"Sent frame_id={payload['frame_id']}")

if __name__ == "__main__":
    main()
