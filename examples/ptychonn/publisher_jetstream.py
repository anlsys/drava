import asyncio
import os
import time
from nats.aio.client import Client as NATS
from publisher_util import (
    load_publish_config,
    load_transport_config,
    make_payload_generator,
)

NATS_URL, STREAM, SUBJECT = load_transport_config()
EOS_PREFIX = b"DRAVA_EOS:"
RATE_HZ, SYNTHETIC_MODE, TARGET_FRAMES = load_publish_config()
LOG_EVERY = 1024
PUBLISH_INFLIGHT = 1024


async def main():
    nc = NATS()
    await nc.connect(NATS_URL)
    js = nc.jetstream()

    try:
        await js.add_stream(name=STREAM, subjects=[SUBJECT])
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
    last_ack_seq = None
    inflight_limit = PUBLISH_INFLIGHT
    pending = []

    async def flush_pending():
        nonlocal pending, last_ack_seq
        if not pending:
            return
        acks = await asyncio.gather(*pending)
        pending = []
        if acks:
            last_ack_seq = acks[-1].seq

    while sent_count < TARGET_FRAMES:
        source_idx = sent_count
        payload = next_payload(source_idx)
        pending.append(asyncio.create_task(js.publish(SUBJECT, payload)))
        if len(pending) >= inflight_limit:
            await flush_pending()
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
                f"Published count={sent_count} seq={last_ack_seq if last_ack_seq is not None else 'n/a'} "
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

    n_frames = sent_count
    print(f"Fixed-frame completion: n_frames={n_frames}")

    await flush_pending()

    # End-of-stream marker with sent frame count
    eos_payload = EOS_PREFIX + str(n_frames).encode("ascii")
    eos_ack = await js.publish(SUBJECT, eos_payload)
    await nc.drain()
    t_end = time.perf_counter()
    total_dt = t_end - t0
    final_seq = last_ack_seq if last_ack_seq is not None else "n/a"
    print(
        f"Done: published {sent_count} frames in {total_dt:.3f}s "
        f"(avg_fps={sent_count / total_dt:.2f}) seq={final_seq} eos_seq={eos_ack.seq} "
        f"Last frame sent at: {t_end}"
    )


if __name__ == "__main__":
    asyncio.run(main())
