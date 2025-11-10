# publisher.py
import asyncio, json, base64, numpy as np, time
from nats.aio.client import Client as NATS
import pandas as pd

STREAM  = "FRAMES"
SUBJECT = "frames.raw"

async def main():
    nc = NATS(); await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    try: await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception: pass
    # Prepare one-row iris sample
    feature_names = ['sepal length (cm)', 'sepal width (cm)', 'petal length (cm)', 'petal width (cm)']
    new_data_df = pd.DataFrame(
        np.array([[5.1, 3.5, 1.4, 0.2]], dtype=np.float32),
        columns=feature_names
    )
    arr = new_data_df.to_numpy(copy=False)
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



