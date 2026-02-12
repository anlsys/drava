import asyncio, time
import numpy as np
from nats.aio.client import Client as NATS

STREAM = "FRAMES"
SUBJECT = "frames.raw"
DATA_DIR = "PtychoNN_data_partial"

# target framerate: set to None or 0 for max speed
RATE_HZ = 1000.0
LOG_EVERY = 256

async def main():
    nc = NATS()
    await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    try:
        await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception:
        pass

    X_test = np.load(f"{DATA_DIR}/X_test.npy").astype("float32")
    total_frames = X_test.shape[0]
    print("X_test shape:", X_test.shape)

    # Pacing setup
    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    next_t = (t0 + period) if pacing else None

    for idx in range(total_frames):
        frame = X_test[idx]
        payload = frame.tobytes(order="C")
        ack = await js.publish(SUBJECT, payload)
        win_count += 1
        if idx == 0:
            print(f"First frame sent at:{t0}")


        if (idx + 1) % LOG_EVERY == 0 or idx == total_frames - 1:
            now = time.perf_counter()
            dt_total = now - t0
            dt_win = now - win_t0

            avg_fps = (idx + 1) / dt_total if dt_total > 0 else float("inf")
            win_fps = win_count / dt_win if dt_win > 0 else float("inf")

            print(
                f"Published idx={idx}/{total_frames} seq={ack.seq} "
                f"win_fps={win_fps:.2f} avg_fps={avg_fps:.2f}"
            )

            win_t0 = now
            win_count = 0

        # Pace only if enabled
        if pacing:
            sleep_s = next_t - time.perf_counter()
            if sleep_s > 0:
                await asyncio.sleep(sleep_s)
            next_t += period

    await nc.drain()

    total_dt = time.perf_counter() - t0
    print(
        f"Done: published {total_frames} frames in {total_dt:.3f}s "
        f"(avg_fps={total_frames/total_dt:.2f})"
    )

if __name__ == "__main__":
    asyncio.run(main())
