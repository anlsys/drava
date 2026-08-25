"""PtychoNN socket publisher.

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

from drava_common import load_publish_config, socket_publish_stream  # noqa: E402
from publisher_util import make_payload_generator  # noqa: E402

FIFO_PATH = os.getenv("DRAVA_OUTPUT_FIFO_PATH", "/tmp/drava_in")


def main():
    rate_hz, synthetic_mode, num_frames = load_publish_config()
    next_payload = make_payload_generator(synthetic_mode)
    socket_publish_stream(FIFO_PATH, next_payload, num_frames, rate_hz=rate_hz)


if __name__ == "__main__":
    main()
