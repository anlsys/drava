import asyncio
import json
import os
import time
from pathlib import Path

from nats.aio.client import Client as NATS
from nats.js.errors import APIError


EOS_PREFIX = b"DRAVA_EOS:"
PUBLISH_INFLIGHT = int(os.getenv("DRAVA_PUBLISH_INFLIGHT", "1024"))
PUBLISH_RETRIES = int(os.getenv("DRAVA_PUBLISH_RETRIES", "8"))
PUBLISH_RETRY_DELAY_S = float(os.getenv("DRAVA_PUBLISH_RETRY_DELAY_S", "0.05"))
LOG_EVERY = int(os.getenv("DRAVA_PUBLISH_LOG_EVERY", "10000"))


def _stage_config_path():
    cfg_path = os.getenv("DRAVA_STAGE_CONFIG", "")
    if not cfg_path:
        return None
    path = Path(cfg_path)
    return path if path.exists() else None


def _section_scalar(path: Path | None, section: str, key_name: str):
    if path is None:
        return None
    in_section = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0 and body == f"{section}:":
            in_section = True
            continue
        if indent == 0 and body.endswith(":") and body != f"{section}:":
            in_section = False
            continue
        if in_section and indent >= 2 and ":" in body:
            key, value = body.split(":", 1)
            if key.strip() == key_name:
                return value.strip().strip("\"'")
    return None


def _stage_ingress_scalar(path: Path | None, stage_name: str, key_name: str):
    if path is None:
        return None
    in_stages = False
    in_stage = False
    in_ingress = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if body == "stages:":
            in_stages = True
            in_stage = False
            in_ingress = False
            continue
        if not in_stages:
            continue
        if indent == 2 and body.startswith("- "):
            in_stage = False
            in_ingress = False
            item = body[2:]
            if item.startswith("name:") and item.split(":", 1)[1].strip().strip("\"'") == stage_name:
                in_stage = True
            continue
        if not in_stage:
            continue
        if indent == 4 and body == "ingress:":
            in_ingress = True
            continue
        if indent == 4 and body.endswith(":") and body != "ingress:":
            in_ingress = False
            continue
        if in_ingress and indent >= 6 and ":" in body:
            key, value = body.split(":", 1)
            if key.strip() == key_name:
                return value.strip().strip("\"'")
    return None


def load_config():
    cfg = _stage_config_path()

    nats_url = os.getenv(
        "NATS_URL",
        _section_scalar(cfg, "transport", "nats_url") or "nats://127.0.0.1:4222",
    )
    stream = os.getenv(
        "DRAVA_STREAM",
        _stage_ingress_scalar(cfg, "stage1", "stream") or "FRAMES",
    )
    subject = os.getenv(
        "DRAVA_SUBJECT",
        _stage_ingress_scalar(cfg, "stage1", "subject") or "frames.raw",
    )
    rate_hz = float(os.getenv("DRAVA_PUBLISH_RATE_HZ", _section_scalar(cfg, "publisher", "rate_hz") or "0"))
    num_frames = int(os.getenv("DRAVA_PUBLISH_NUM_FRAMES", _section_scalar(cfg, "publisher", "num_frames") or "10000"))
    payload_bytes = int(os.getenv("DRAVA_BARE_PAYLOAD_BYTES", _section_scalar(cfg, "publisher", "payload_bytes") or "1"))
    if num_frames <= 0:
        raise RuntimeError("DRAVA_PUBLISH_NUM_FRAMES must be positive")
    if payload_bytes <= 0:
        raise RuntimeError("DRAVA_BARE_PAYLOAD_BYTES must be positive")
    print(
        "bare-runtime publisher: "
        f"url={nats_url} stream={stream} subject={subject} "
        f"frames={num_frames} payload_bytes={payload_bytes} rate_hz={rate_hz}"
    )
    return nats_url, stream, subject, rate_hz, num_frames, payload_bytes


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
    nats_url, stream, subject, rate_hz, target_frames, payload_bytes = load_config()
    payload = b"\0" * payload_bytes

    nc = NATS()
    await nc.connect(nats_url)
    js = nc.jetstream()

    try:
        await js.add_stream(name=stream, subjects=[subject])
    except Exception:
        pass

    pacing = rate_hz > 0
    period = (1.0 / rate_hz) if pacing else None
    next_t = None

    t0 = time.perf_counter()
    win_t0 = t0
    win_count = 0
    sent_count = 0
    last_ack_seq = None
    pending = []
    if pacing:
        next_t = t0 + period

    async def flush_pending():
        nonlocal pending, last_ack_seq
        if not pending:
            return
        acks = await asyncio.gather(*pending)
        pending = []
        if acks:
            last_ack_seq = acks[-1].seq

    while sent_count < target_frames:
        pending.append(asyncio.create_task(publish_with_retry(js, subject, payload)))
        if len(pending) >= PUBLISH_INFLIGHT:
            await flush_pending()

        sent_count += 1
        win_count += 1
        if sent_count == 1:
            print(f"First frame sent at: {t0}")

        if LOG_EVERY > 0 and sent_count % LOG_EVERY == 0:
            now = time.perf_counter()
            dt_total = now - t0
            dt_win = now - win_t0
            print(
                f"Published count={sent_count} seq={last_ack_seq if last_ack_seq is not None else 'n/a'} "
                f"win_fps={win_count / dt_win if dt_win > 0 else float('inf'):.2f} "
                f"avg_fps={sent_count / dt_total if dt_total > 0 else float('inf'):.2f}"
            )
            win_t0 = now
            win_count = 0

        if pacing:
            assert next_t is not None
            sleep_s = next_t - time.perf_counter()
            if sleep_s > 0:
                await asyncio.sleep(sleep_s)
            next_t += period

    await flush_pending()
    eos_payload = EOS_PREFIX + str(sent_count).encode("ascii")
    eos_ack = await publish_with_retry(js, subject, eos_payload)
    await nc.drain()

    t_end = time.perf_counter()
    total_dt = t_end - t0
    avg_fps = sent_count / total_dt if total_dt > 0 else 0.0
    print(
        f"Done: published {sent_count} frames in {total_dt:.3f}s "
        f"(avg_fps={avg_fps:.2f}) "
        f"seq={last_ack_seq if last_ack_seq is not None else 'n/a'} eos_seq={eos_ack.seq}"
    )
    # Report publisher metrics to a file (mirrors the runtime's file-based
    # metrics) so orchestrators read files instead of scraping stdout. No-op
    # when DRAVA_PUBLISHER_METRICS_FILE is unset.
    _metrics_path = os.getenv("DRAVA_PUBLISHER_METRICS_FILE")
    if _metrics_path:
        with open(_metrics_path, "w", encoding="utf-8") as _mf:
            json.dump(
                {
                    "frames": int(sent_count),
                    "duration_s": float(total_dt),
                    "avg_fps": float(avg_fps),
                    "eos_seq": int(eos_ack.seq),
                },
                _mf,
            )


if __name__ == "__main__":
    asyncio.run(main())
