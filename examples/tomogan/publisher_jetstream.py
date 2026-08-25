"""TomoGAN JetStream publisher.

Publishes real tomography frames from the dataset to stage1 over JetStream. All
generic plumbing (connect, pacing, in-flight window, retry/backoff, EOS,
metrics) lives in ``drava_common``; this file only loads the dataset payloads.
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
from publisher_util import load_dataset_payloads  # noqa: E402


async def main():
    nats_url, stream, subject = load_transport_config()
    rate_hz, num_frames = load_publish_config()

    payloads = load_dataset_payloads()
    n = len(payloads)

    def next_payload(i):
        return payloads[i % n]

    js = await connect_jetstream(nats_url, stream, subject)
    await publish_stream(js, subject, next_payload, num_frames, rate_hz=rate_hz)


if __name__ == "__main__":
    asyncio.run(main())
