# Frame by frame publisher
import asyncio, json, base64, time
import numpy as np
from nats.aio.client import Client as NATS

STREAM = "FRAMES"
SUBJECT = "frames.raw"

PATCH_SIDE = 64
DATA_DIR = "PtychoNN_data_partial"

async def main():
    nc = NATS()
    await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    try:
        await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception:
        pass

    X_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")  # (N,64,64,1)
    n_patches = X_test.shape[0]
    print("X_test shape:", X_test.shape)

    job_id = int(time.time_ns())

    for idx in range(n_patches):
        frame = X_test[idx]  # (64,64,1)

        payload = {
            "kind": "ptychonn_frame",
            "job_id": job_id,
            "frame_id": int(time.time_ns()),
            "idx": idx,                 # single frame index
            "rows": 1,
            "patch_side": PATCH_SIDE,
            "dtype": "float32",
            "order": "C",
            "data_b64": base64.b64encode(frame.tobytes(order="C")).decode(),
            "n_total": n_patches,
        }

        ack = await js.publish(SUBJECT, json.dumps(payload).encode())

        # Optional progress logging
        if idx % 256 == 0 or idx == n_patches - 1:
            print(f"Published idx={idx}/{n_patches-1} seq={ack.seq}")

    await nc.drain()

if __name__ == "__main__":
    asyncio.run(main())
