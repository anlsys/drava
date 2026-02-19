#!/usr/bin/env python3
import struct
import numpy as np

FIFO_PATH = "/tmp/drava_in"

def build_frame_bytes():
    frame = np.array([5.1, 3.5, 1.4, 0.2], dtype=np.float32)
    return frame.tobytes(order="C")

def main():
    print(f"Opening FIFO {FIFO_PATH} for writing.")
    print("Press Enter to send a frame. Press Ctrl+C to quit.\n")

    # Open FIFO once and keep it open
    with open(FIFO_PATH, "wb") as f:
        while True:
            input("Press Enter to send frame...")
            payload = build_frame_bytes()
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            f.flush()
            print("Sent raw frame")

if __name__ == "__main__":
    main()
