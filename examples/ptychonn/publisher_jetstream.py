# publisher_jetstream.py
import asyncio, json, base64, time
import numpy as np
from nats.aio.client import Client as NATS

STREAM = "FRAMES"
SUBJECT = "frames.raw"

PATCH_SIDE = 64
BATCH_SIZE = 32

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

        ack = await js.publish(SUBJECT, json.dumps(payload).encode())
        print(f"Published [{start}:{end}] seq={ack.seq}")

    await nc.drain()

if __name__ == "__main__":
    asyncio.run(main())
