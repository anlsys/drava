import drava
import numpy as np

FRAME_DTYPE = np.float32
FRAME_VALUES = 4
FRAME_BYTES = FRAME_VALUES * np.dtype(FRAME_DTYPE).itemsize


def func(frames):
    for frame in frames:
        if len(frame) != FRAME_BYTES:
            raise ValueError(
                f"payload mismatch: got {len(frame)} bytes, expected {FRAME_BYTES}"
            )
        values = np.frombuffer(frame, dtype=FRAME_DTYPE, count=FRAME_VALUES)
        print(f"Python app received raw frame: {values.tolist()}")

drava.run(func)
