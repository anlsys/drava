"""Publisher for the base_index ordering regression test.

Sends frames whose payload starts with the frame's own 0-based stream
position, then the EOS marker. Deliberately dependency-free (no numpy, no
drava_common) so the test can run anywhere the socket transport does.

Wire format per frame, matching the Drava socket transport:
    [4-byte big-endian length][payload]
Payload:
    [8-byte big-endian sequence number][padding to PAYLOAD_BYTES]
"""
import os
import struct
import sys

SEQ_FMT = "!Q"
SEQ_SIZE = struct.calcsize(SEQ_FMT)
EOS_PREFIX = b"DRAVA_EOS:"

FIFO_PATH = os.getenv("DRAVA_FIFO_PATH", "/tmp/drava_in")
NUM_FRAMES = int(os.getenv("DRAVA_TEST_NUM_FRAMES", "4096"))
# Large enough that batches take real work to move, small enough to stay quick.
PAYLOAD_BYTES = int(os.getenv("DRAVA_TEST_PAYLOAD_BYTES", "1024"))


def main() -> int:
    if PAYLOAD_BYTES < SEQ_SIZE:
        print(f"payload must be >= {SEQ_SIZE} bytes", file=sys.stderr)
        return 2
    if not os.path.exists(FIFO_PATH):
        print(f"FIFO {FIFO_PATH} does not exist", file=sys.stderr)
        return 2

    filler = b"\x00" * (PAYLOAD_BYTES - SEQ_SIZE)
    with open(FIFO_PATH, "wb") as fh:
        for i in range(NUM_FRAMES):
            payload = struct.pack(SEQ_FMT, i) + filler
            fh.write(struct.pack("!I", len(payload)))
            fh.write(payload)
        fh.flush()

        eos = EOS_PREFIX + str(NUM_FRAMES).encode("ascii")
        fh.write(struct.pack("!I", len(eos)))
        fh.write(eos)
        fh.flush()

    print(f"[publisher] sent {NUM_FRAMES} frames of {PAYLOAD_BYTES}B + EOS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
