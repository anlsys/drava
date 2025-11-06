# subscriber.py
import asyncio, json, base64, numpy as np
from nats.aio.client import Client as NATS
import nats.errors as nats_errors

STREAM  = "FRAMES"
SUBJECT = "frames.raw"
DURABLE = "frames_consumer_v2"

def to_numpy(rows, cols, dtype, raw_bytes):
    m = {"float32": np.float32, "float64": np.float64,
         "int32": np.int32, "int16": np.int16, "uint8": np.uint8}
    return np.frombuffer(raw_bytes, dtype=m[dtype]).reshape(rows, cols)

async def main():
    nc = NATS(); await nc.connect("nats://127.0.0.1:4222")
    js = nc.jetstream()

    sub = await js.pull_subscribe(SUBJECT, durable=DURABLE, stream=STREAM)

    while True:
        try:
            msgs = await sub.fetch(1, timeout=2)
        except nats_errors.TimeoutError:
            continue

        for m in msgs:
            try:
                md = m.metadata  # JetStream metadata
                payload = json.loads(m.data.decode())
                arr = to_numpy(int(payload["rows"]), int(payload["cols"]),
                               payload["dtype"], base64.b64decode(payload["data_b64"]))

                print(
                    f"[stream_seq={md.sequence.stream} consumer_seq={md.sequence.consumer}] "
                    f"frame_id={payload.get('frame_id')} shape={arr.shape} dtype={arr.dtype}"
                )
                # print(arr)  # optional: comment out to keep output compact
                await m.ack()
            except Exception as e:
                print("Process error:", e); await m.nak()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass



