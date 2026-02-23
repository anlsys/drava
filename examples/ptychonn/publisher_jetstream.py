import asyncio, time
from nats.aio.client import Client as NATS
from publisher_util import load_publish_config, make_payload_generator

STREAM = "FRAMES"
SUBJECT = "frames.raw"
RATE_HZ, SYNTHETIC_MODE, RUN_SECONDS = load_publish_config()
LOG_EVERY = 256


async def main():
    nc = NATS()
    await nc.connect("nats://0.0.0.0:4222")
    js = nc.jetstream()

    try:
        await js.add_stream(name=STREAM, subjects=["frames.*"])
    except Exception:
        pass

    next_payload = make_payload_generator(SYNTHETIC_MODE)

    # Pacing setup
    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    next_t = (t0 + period) if pacing else None
    sent_count = 0
    last_ack = None

    while True:
        elapsed = time.perf_counter() - t0
        if elapsed >= RUN_SECONDS:
            break
        source_idx = sent_count
        payload = next_payload(source_idx)
        last_ack = await js.publish(SUBJECT, payload)
        sent_count += 1
        win_count += 1
        if sent_count == 1:
            print(f"First frame sent at:{t0}")

        if sent_count % LOG_EVERY == 0:
            now = time.perf_counter()
            dt_total = now - t0
            dt_win = now - win_t0

            avg_fps = sent_count / dt_total if dt_total > 0 else float("inf")
            win_fps = win_count / dt_win if dt_win > 0 else float("inf")

            print(
                f"Published count={sent_count} seq={last_ack.seq} "
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
    t_end = time.perf_counter()
    total_dt = t_end - t0
    final_seq = last_ack.seq if last_ack is not None else "n/a"
    print(
        f"Done: published {sent_count} frames in {total_dt:.3f}s "
        f"(avg_fps={sent_count / total_dt:.2f}) seq={final_seq} "
        f"Last frame sent at: {t_end}"
    )


if __name__ == "__main__":
    asyncio.run(main())
