"""TomoGAN socket publisher.

Frame-by-frame publisher for the Drava socket transport (FIFO -> socat -> UNIX
socket). Wire format per frame: [4-byte big-endian length][raw bytes]. All
generic plumbing (pacing, EOS, metrics) lives in ``drava_common``.

Prereqs (example):
  mkfifo /tmp/drava_in
  socat /tmp/drava_in UNIX-LISTEN:/tmp/accel_2048.sock,fork
"""
import os
import sys

# Make the shared examples/common package importable without installation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from drava_common import socket_publish_stream  # noqa: E402
# TomoGAN's load_publish_config returns (rate_hz, num_frames) and defaults
# num_frames to the dataset size.
from publisher_util import load_dataset_payloads, load_publish_config  # noqa: E402

FIFO_PATH = os.getenv("DRAVA_OUTPUT_FIFO_PATH", "/tmp/drava_in")


def main():
    rate_hz, num_frames = load_publish_config()
    payloads = load_dataset_payloads()
    n = len(payloads)

    def next_payload(i):
        return payloads[i % n]

    socket_publish_stream(FIFO_PATH, next_payload, num_frames, rate_hz=rate_hz)


if __name__ == "__main__":
    main()
