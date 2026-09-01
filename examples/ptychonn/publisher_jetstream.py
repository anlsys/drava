"""PtychoNN JetStream publisher.

Data source for stage1 over NATS JetStream. All generic plumbing (connect,
pacing, in-flight window, retry/backoff, EOS, metrics) lives in
``drava_common``; this file only picks the payload source.
"""
import asyncio
import os
import sys

# Make the shared examples/common package importable without installation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from drava_common import (  # noqa: E402
    connect_jetstream,
    load_publish_config,
    load_transport_config,
    publish_stream,
)
from publisher_util import make_payload_generator  # noqa: E402


async def main():
    nats_url, stream, subject = load_transport_config()
    rate_hz, synthetic_mode, num_frames = load_publish_config()
    next_payload = make_payload_generator(synthetic_mode)

    js = await connect_jetstream(nats_url, stream, subject)
    await publish_stream(js, subject, next_payload, num_frames, rate_hz=rate_hz)


if __name__ == "__main__":
    asyncio.run(main())
