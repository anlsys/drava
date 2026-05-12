import asyncio
import os
import time

from nats.aio.client import Client as NATS
from nats.js.errors import APIError

from publisher_util import (
    load_dataset_payloads,
    load_publish_config,
    load_transport_config,
)

NATS_URL, STREAM, SUBJECT = load_transport_config()
EOS_PREFIX = b"DRAVA_EOS:"
RATE_HZ, TARGET_FRAMES = load_publish_config()
LOG_EVERY = 128
PUBLISH_INFLIGHT = int(os.getenv("DRAVA_PUBLISH_INFLIGHT", "64"))
PUBLISH_RETRIES = int(os.getenv("DRAVA_PUBLISH_RETRIES", "8"))
PUBLISH_RETRY_DELAY_S = float(os.getenv("DRAVA_PUBLISH_RETRY_DELAY_S", "0.05"))


async def publish_with_retry(js, subject, payload):
    delay_s = PUBLISH_RETRY_DELAY_S
    for attempt in range(PUBLISH_RETRIES + 1):
        try:
            return await js.publish(subject, payload)
        except APIError as exc:
            if getattr(exc, "err_code", None) != 10167 or attempt >= PUBLISH_RETRIES:
                raise
            await asyncio.sleep(delay_s)
            delay_s *= 2.0


async def main():
    nc = NATS()
    await nc.connect(NATS_URL)
    js = nc.jetstream()

    try:
        await js.add_stream(name=STREAM, subjects=[SUBJECT])
    except Exception:
        pass

    payloads = load_dataset_payloads()
    n_payloads = len(payloads)
    pacing = RATE_HZ is not None and RATE_HZ > 0
    period = (1.0 / RATE_HZ) if pacing else None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0

    next_t = (t0 + period) if pacing else None
    sent_count = 0
    last_ack_seq = None
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
        payload = payloads[sent_count % n_payloads]
        pending.append(asyncio.create_task(publish_with_retry(js, SUBJECT, payload)))
        if len(pending) >= PUBLISH_INFLIGHT:
            await flush_pending()

        sent_count += 1
        win_count += 1
        if sent_count == 1:
            print(f"First frame sent at: {t0}")

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

        if pacing:
            sleep_s = next_t - time.perf_counter()
            if sleep_s > 0:
                await asyncio.sleep(sleep_s)
            next_t += period

    await flush_pending()

    eos_payload = EOS_PREFIX + str(sent_count).encode("ascii")
    eos_ack = await publish_with_retry(js, SUBJECT, eos_payload)
    await nc.drain()

    t_end = time.perf_counter()
    total_dt = t_end - t0
    print(
        f"Done: published {sent_count} frames in {total_dt:.3f}s "
        f"(avg_fps={sent_count / total_dt:.2f}) "
        f"seq={last_ack_seq if last_ack_seq is not None else 'n/a'} eos_seq={eos_ack.seq}"
    )


if __name__ == "__main__":
    asyncio.run(main())
