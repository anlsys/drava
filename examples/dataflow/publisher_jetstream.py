import asyncio
import numpy as np
from nats.aio.client import Client as NATS

STREAM  = "FRAMES"
SUBJECT = "frames.raw"

async def main():
    nc = NATS(); await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    try: await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception: pass
    frame = np.array([5.1, 3.5, 1.4, 0.2], dtype=np.float32)
    payload = frame.tobytes(order="C")
    ack = await js.publish(SUBJECT, payload)
    print(f"Published raw frame to {SUBJECT}, sequence={ack.seq}")
    await nc.drain()

if __name__ == "__main__":
    asyncio.run(main())


