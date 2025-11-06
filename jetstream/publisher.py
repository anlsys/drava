# publisher.py
import asyncio, json, base64, numpy as np, time
from nats.aio.client import Client as NATS

STREAM  = "FRAMES"
SUBJECT = "frames.raw"

async def main():
    nc = NATS(); await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    try: await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception: pass

    arr = (np.arange(6, dtype=np.float32) + 1).reshape(2, 3)
    payload = {
        "rows": arr.shape[0],
        "cols": arr.shape[1],
        "dtype": "float32",
        "order": "C",
        "frame_id": int(time.time_ns()),  # unique each run
        "data_b64": base64.b64encode(arr.tobytes(order="C")).decode(),
    }
    ack = await js.publish(SUBJECT, json.dumps(payload).encode())
    print(f"Published frame to {SUBJECT}, sequence={ack.seq}")
    await nc.drain()

if __name__ == "__main__":
    asyncio.run(main())



