"""Shared publisher helpers for Drava example data-source processes.

Publishers are *not* the runtime: they are plain NATS/socket clients that feed
frames into stage1 and emit the end-of-stream (EOS) marker. Every example used
to copy the same pacing loop, EOS emission, metrics writer, and config
resolution. That lives here now; an example publisher only supplies a payload
generator and picks the transport.

Config precedence matches the documented rule for publishers: an explicit env
var wins, otherwise the value from ``pipeline.yaml`` (via ``DRAVA_STAGE_CONFIG``),
otherwise a built-in default.
"""

from __future__ import annotations

import json
import os
import struct
import time
from pathlib import Path
from typing import Callable, Optional

from .config import PipelineConfigError, load_pipeline_config

EOS_PREFIX = b"DRAVA_EOS:"

# JetStream "maximum messages exceeded" — the consumer is behind; retry with
# backoff rather than dropping the frame.
_JS_MAX_MSGS_ERR_CODE = 10167


async def connect_jetstream(nats_url: str, stream: str, subject: str):
    """Connect to NATS and ensure ``stream`` exists carrying ``subject``.

    Returns a JetStream context ready for ``publish_stream``. Idempotent: an
    already-existing stream is fine. Keeps the NATS client alive on the returned
    context (``._nc``) so callers can ``await ctx._nc.drain()`` at the end.
    """
    from nats.aio.client import Client as NATS

    nc = NATS()
    await nc.connect(nats_url)
    js = nc.jetstream()
    try:
        await js.add_stream(name=stream, subjects=[subject])
    except Exception:
        # Stream already exists (or is managed elsewhere); publishing still works.
        pass
    # Stash the client so the caller can drain/close it.
    setattr(js, "_nc", nc)
    return js


async def _js_publish_with_retry(js, subject, payload, retries, delay_s):
    """Publish once, retrying with exponential backoff on JetStream overflow."""
    try:
        from nats.js.errors import APIError
    except Exception:  # pragma: no cover - nats not installed
        APIError = ()  # type: ignore

    delay = delay_s
    for attempt in range(retries + 1):
        try:
            return await js.publish(subject, payload)
        except APIError as exc:  # type: ignore[misc]
            import asyncio

            if getattr(exc, "err_code", None) != _JS_MAX_MSGS_ERR_CODE or attempt >= retries:
                raise
            await asyncio.sleep(delay)
            delay *= 2.0


# --------------------------------------------------------------------------- #
# Config resolution (env overrides YAML overrides default)
# --------------------------------------------------------------------------- #
def _pipeline_or_none():
    cfg_path = os.getenv("DRAVA_STAGE_CONFIG", "")
    if not cfg_path:
        return None
    try:
        return load_pipeline_config(cfg_path)
    except PipelineConfigError:
        return None


def load_transport_config():
    """Return ``(nats_url, stream, subject)`` for feeding stage1.

    Env vars ``NATS_URL`` / ``DRAVA_STREAM`` / ``DRAVA_SUBJECT`` override the
    corresponding YAML values (``transport.nats_url`` and stage1's ingress).
    """
    cfg = _pipeline_or_none()
    yaml_url = cfg.nats_url if cfg else "nats://0.0.0.0:4222"
    yaml_stream = "FRAMES"
    yaml_subject = "frames.raw"
    if cfg is not None:
        try:
            s1 = cfg.stage("stage1")
            yaml_stream = str(s1.ingress.get("stream", yaml_stream))
            yaml_subject = str(s1.ingress.get("subject", yaml_subject))
        except PipelineConfigError:
            pass

    nats_url = os.getenv("NATS_URL", yaml_url)
    stream = os.getenv("DRAVA_STREAM", yaml_stream)
    subject = os.getenv("DRAVA_SUBJECT", yaml_subject)
    return nats_url, stream, subject


def load_publish_config(default_num_frames: Optional[int] = None):
    """Return ``(rate_hz, synthetic_mode, num_frames)``.

    - ``DRAVA_PUBLISH_RATE_HZ`` overrides ``publisher.rate_hz`` (default 0 = max).
    - ``DRAVA_PUBLISH_SYNTHETIC`` overrides ``publisher.synthetic`` (default off).
    - ``DRAVA_PUBLISH_NUM_FRAMES`` overrides ``publisher.num_frames``. If neither
      is set, ``default_num_frames`` is used (e.g. a dataset size); if that is
      also None, raises.
    """
    cfg = _pipeline_or_none()
    pub = {}
    if cfg is not None:
        pub = cfg.raw.get("publisher", {}) or {}
        if not isinstance(pub, dict):
            pub = {}

    rate_hz = float(os.getenv("DRAVA_PUBLISH_RATE_HZ", str(pub.get("rate_hz", 0))))

    synth_env = os.getenv("DRAVA_PUBLISH_SYNTHETIC")
    if synth_env is not None:
        synthetic_mode = synth_env == "1"
    else:
        synthetic_mode = bool(pub.get("synthetic", False))

    num_env = os.getenv("DRAVA_PUBLISH_NUM_FRAMES")
    if num_env not in (None, ""):
        num_frames = int(num_env)
    elif pub.get("num_frames") not in (None, ""):
        num_frames = int(pub["num_frames"])
    elif default_num_frames is not None:
        num_frames = int(default_num_frames)
    else:
        raise PipelineConfigError(
            "Publisher requires a frame count. Set DRAVA_PUBLISH_NUM_FRAMES, "
            "publisher.num_frames in the stage config, or pass default_num_frames."
        )

    print(
        f"[publisher] rate_hz={rate_hz} synthetic={synthetic_mode} "
        f"num_frames={num_frames}"
    )
    return rate_hz, synthetic_mode, num_frames


def write_publisher_metrics(frames, duration_s, avg_fps, eos_seq=None):
    """Write a single JSON metrics object to ``$DRAVA_PUBLISHER_METRICS_FILE``.

    No-op when the env var is unset. Mirrors the runtime's file-based metrics so
    orchestrators read files instead of scraping stdout.
    """
    path = os.getenv("DRAVA_PUBLISHER_METRICS_FILE")
    if not path:
        return
    obj = {
        "frames": int(frames),
        "duration_s": float(duration_s),
        "avg_fps": float(avg_fps),
    }
    if eos_seq is not None:
        obj["eos_seq"] = int(eos_seq)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


# --------------------------------------------------------------------------- #
# Pacing + progress logging shared by both transports
# --------------------------------------------------------------------------- #
class _Pacer:
    def __init__(self, rate_hz: float, log_every: int, t0: float):
        self.pacing = rate_hz is not None and rate_hz > 0
        self.period = (1.0 / rate_hz) if self.pacing else None
        self.log_every = log_every
        self.t0 = t0
        self.win_t0 = t0
        self.win_count = 0
        self.next_t = (t0 + self.period) if self.pacing else None

    def tick(self, sent_count: int, extra: str = "", sleeper=time.sleep):
        self.win_count += 1
        if sent_count == 1:
            print(f"[publisher] first frame at t={self.t0:.6f}")
        if self.log_every and sent_count % self.log_every == 0:
            now = time.perf_counter()
            dt_total = now - self.t0
            dt_win = now - self.win_t0
            avg = sent_count / dt_total if dt_total > 0 else float("inf")
            win = self.win_count / dt_win if dt_win > 0 else float("inf")
            print(
                f"[publisher] count={sent_count} win_fps={win:.2f} "
                f"avg_fps={avg:.2f}{(' ' + extra) if extra else ''}"
            )
            self.win_t0 = now
            self.win_count = 0
        if self.pacing:
            sleep_s = self.next_t - time.perf_counter()
            if sleep_s > 0:
                sleeper(sleep_s)
            self.next_t += self.period


async def publish_stream(
    js,
    subject: str,
    next_payload: Callable[[int], bytes],
    num_frames: int,
    rate_hz: float = 0.0,
    log_every: int = 1024,
    inflight: int = 1024,
    retries: int = 8,
    retry_delay_s: float = 0.05,
    drain: bool = True,
):
    """Publish ``num_frames`` payloads to a JetStream ``subject`` then an EOS.

    ``js`` is a NATS JetStream context (e.g. from :func:`connect_jetstream`);
    ``next_payload(i)`` returns the bytes for frame ``i``. Handles pacing,
    an in-flight publish window, retry-with-backoff on JetStream overflow, the
    end-of-stream marker, windowed FPS logging, and metrics.

    Returns ``(sent_count, duration_s, avg_fps, eos_seq)`` and writes publisher
    metrics if ``$DRAVA_PUBLISHER_METRICS_FILE`` is set. If ``drain`` and the
    context exposes its NATS client (``js._nc``), the client is drained at the
    end so all acks land before exit.
    """
    import asyncio

    t0 = time.perf_counter()
    pacing = rate_hz is not None and rate_hz > 0
    period = (1.0 / rate_hz) if pacing else None
    next_t = (t0 + period) if pacing else None
    win_t0 = t0
    win_count = 0
    sent_count = 0
    last_ack_seq = None
    pending = []

    async def flush():
        nonlocal pending, last_ack_seq
        if not pending:
            return
        acks = await asyncio.gather(*pending)
        pending = []
        if acks:
            last_ack_seq = getattr(acks[-1], "seq", last_ack_seq)

    while sent_count < num_frames:
        payload = next_payload(sent_count)
        pending.append(
            asyncio.create_task(
                _js_publish_with_retry(js, subject, payload, retries, retry_delay_s)
            )
        )
        if len(pending) >= inflight:
            await flush()
        sent_count += 1
        win_count += 1
        if sent_count == 1:
            print(f"[publisher] first frame at t={t0:.6f}")
        if log_every and sent_count % log_every == 0:
            now = time.perf_counter()
            dt_total = now - t0
            dt_win = now - win_t0
            avg = sent_count / dt_total if dt_total > 0 else float("inf")
            win = win_count / dt_win if dt_win > 0 else float("inf")
            print(
                f"[publisher] count={sent_count} "
                f"seq={last_ack_seq if last_ack_seq is not None else 'n/a'} "
                f"win_fps={win:.2f} avg_fps={avg:.2f}"
            )
            win_t0 = now
            win_count = 0
        if pacing:
            sleep_s = next_t - time.perf_counter()
            if sleep_s > 0:
                await asyncio.sleep(sleep_s)
            next_t += period

    await flush()
    eos_payload = EOS_PREFIX + str(sent_count).encode("ascii")
    eos_ack = await _js_publish_with_retry(
        js, subject, eos_payload, retries, retry_delay_s
    )

    if drain:
        nc = getattr(js, "_nc", None)
        if nc is not None:
            try:
                await nc.drain()
            except Exception:
                pass

    t_end = time.perf_counter()
    duration_s = t_end - t0
    avg_fps = sent_count / duration_s if duration_s > 0 else 0.0
    eos_seq = getattr(eos_ack, "seq", None)
    print(
        f"[publisher] done: {sent_count} frames in {duration_s:.3f}s "
        f"(avg_fps={avg_fps:.2f}) eos_seq={eos_seq}"
    )
    write_publisher_metrics(sent_count, duration_s, avg_fps, eos_seq=eos_seq)
    return sent_count, duration_s, avg_fps, eos_seq


def socket_publish_stream(
    fifo_path: str,
    next_payload: Callable[[int], bytes],
    num_frames: int,
    rate_hz: float = 0.0,
    log_every: int = 256,
):
    """Publish ``num_frames`` payloads to a Drava socket FIFO then an EOS.

    Wire format per frame: ``[4-byte big-endian length][raw bytes]``. Returns
    ``(sent_count, duration_s, avg_fps)`` and writes publisher metrics if set.
    """
    if not os.path.exists(fifo_path):
        raise RuntimeError(
            f"FIFO {fifo_path} does not exist. Create it (mkfifo {fifo_path}) and "
            f"start socat/the Drava socket transport first."
        )

    t0 = time.perf_counter()
    pacer = _Pacer(rate_hz, log_every, t0)
    sent_count = 0

    print(f"[publisher] opening FIFO {fifo_path} for writing...")
    with open(fifo_path, "wb") as f:
        while sent_count < num_frames:
            payload = next_payload(sent_count)
            f.write(struct.pack("!I", len(payload)))
            f.write(payload)
            f.flush()
            sent_count += 1
            pacer.tick(sent_count)

        eos_payload = EOS_PREFIX + str(sent_count).encode("ascii")
        f.write(struct.pack("!I", len(eos_payload)))
        f.write(eos_payload)
        f.flush()

    duration_s = time.perf_counter() - t0
    avg_fps = sent_count / duration_s if duration_s > 0 else 0.0
    print(
        f"[publisher] done: {sent_count} frames in {duration_s:.3f}s "
        f"(avg_fps={avg_fps:.2f})"
    )
    write_publisher_metrics(sent_count, duration_s, avg_fps)
    return sent_count, duration_s, avg_fps
