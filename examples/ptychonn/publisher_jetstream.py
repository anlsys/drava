# publisher_ptychonn.py
import asyncio, json, base64, time
import numpy as np
from nats.aio.client import Client as NATS

STREAM = "FRAMES"
SUBJECT = "frames.raw"

PATCH_SIDE = 64
BATCH_SIZE = 32  # how many patches per message

DATA_DIR = "PtychoNN_data_partial"

async def main():
    # Connect to NATS + JetStream
    nc = NATS()
    await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    # Ensure stream exists
    try:
        await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception:
        pass

    # Load test diffraction patches (inputs only)
    X_test = np.load(f"{DATA_DIR}/X_test.npy")
    print("X_test shape:", X_test.shape)  # e.g. (3600, 64, 64, 1)
    n_patches = X_test.shape[0]

    # Loop over X_test in batches
    for start in range(0, n_patches, BATCH_SIZE):
        end = min(start + BATCH_SIZE, n_patches)
        batch = X_test[start:end]  # shape (B, 64, 64, 1)
        B = batch.shape[0]
        if B == 0:
            break

        # Flatten each patch to 1D: (B, 64*64)
        batch_2d = batch.reshape(B, PATCH_SIDE * PATCH_SIDE).astype("float32")

        payload = {
            "rows": B,
            "cols": PATCH_SIDE * PATCH_SIDE,
            "dtype": "float32",
            "order": "C",
            "frame_id": int(time.time_ns()),  # or start index
            "patch_side": PATCH_SIDE,
            "data_b64": base64.b64encode(batch_2d.tobytes(order="C")).decode(),
        }

        ack = await js.publish(SUBJECT, json.dumps(payload).encode())
        print(f"Published batch [{start}:{end}] -> seq={ack.seq}")

    await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())
