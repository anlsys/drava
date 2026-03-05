import os
import numpy as np

DATA_DIR = "PtychoNN_data_partial"
FRAME_SHAPE = (64, 64, 1)
SYNTHETIC_SEED = 56465
SYNTHETIC_POOL_SIZE = 3600


def load_publish_config():
    rate_hz = float(os.getenv("DRAVA_PUBLISH_RATE_HZ", "1000"))
    synthetic_mode = os.getenv("DRAVA_PUBLISH_SYNTHETIC", "0") == "1"
    run_seconds = float(os.getenv("DRAVA_PUBLISH_DURATION_S", "30"))
    print(f"DRAVA_PUBLISH_RATE_HZ: {rate_hz},"
          f"DRAVA_PUBLISH_SYNTHETIC: {synthetic_mode},"
          f"DRAVA_PUBLISH_DURATION_S: {run_seconds}")
    return rate_hz, synthetic_mode, run_seconds


def compute_square_completion(n_raw):
    if n_raw <= 0:
        return 1, 1, 1
    side = int(np.ceil(np.sqrt(n_raw)))
    n_square = side * side
    extra = n_square - n_raw
    return side, n_square, extra


def make_payload_generator(synthetic_mode):
    if synthetic_mode:
        rng = np.random.default_rng(SYNTHETIC_SEED)
        synthetic_frames = rng.random((SYNTHETIC_POOL_SIZE, *FRAME_SHAPE), dtype=np.float32)
        payloads = [frame.tobytes(order="C") for frame in synthetic_frames]

        def next_payload(i):
            return payloads[i % SYNTHETIC_POOL_SIZE]

        return next_payload

    x_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")
    payloads = [frame.tobytes(order="C") for frame in x_test]
    n_frames = len(payloads)

    def next_payload(i):
        return payloads[i % n_frames]

    return next_payload
