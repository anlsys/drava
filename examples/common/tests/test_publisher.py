"""Unit tests for drava_common.publisher (no real NATS/socket needed).

Run: python examples/common/tests/test_publisher.py
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Keep all scratch inside the repo (see AGENTS.md filesystem rule).
_REPO_TMP = Path(__file__).resolve().parents[3] / ".scratch" / "tests"
_REPO_TMP.mkdir(parents=True, exist_ok=True)

from drava_common.publisher import (  # noqa: E402
    EOS_PREFIX,
    publish_stream,
    socket_publish_stream,
    write_publisher_metrics,
)


class _Ack:
    def __init__(self, seq):
        self.seq = seq


class _FakeJS:
    """Records published (subject, payload) pairs; returns increasing seqs."""

    def __init__(self):
        self.published = []
        self._seq = 0

    async def publish(self, subject, payload):
        self._seq += 1
        self.published.append((subject, payload))
        return _Ack(self._seq)


def test_publish_stream_frames_and_eos():
    js = _FakeJS()

    def next_payload(i):
        return f"frame{i}".encode()

    sent, dur, fps, eos_seq = asyncio.run(
        publish_stream(js, "subj", next_payload, num_frames=5, rate_hz=0, log_every=0)
    )
    assert sent == 5, sent
    # 5 data frames + 1 EOS
    assert len(js.published) == 6, len(js.published)
    assert js.published[-1][1].startswith(EOS_PREFIX)
    assert js.published[-1][1] == EOS_PREFIX + b"5"
    assert eos_seq == 6
    # data payloads intact and in order
    assert [p for _s, p in js.published[:5]] == [f"frame{i}".encode() for i in range(5)]


def test_publish_stream_writes_metrics():
    js = _FakeJS()
    with tempfile.TemporaryDirectory(dir=_REPO_TMP) as d:
        mfile = os.path.join(d, "pub.json")
        os.environ["DRAVA_PUBLISHER_METRICS_FILE"] = mfile
        try:
            asyncio.run(
                publish_stream(js, "s", lambda i: b"x", num_frames=3, log_every=0)
            )
            obj = json.loads(Path(mfile).read_text())
        finally:
            del os.environ["DRAVA_PUBLISHER_METRICS_FILE"]
    assert obj["frames"] == 3
    assert "avg_fps" in obj and "duration_s" in obj and obj["eos_seq"] == 4


def test_publish_stream_retry_on_apierror():
    # The retry branch only catches the real nats APIError; skip when nats is
    # not installed (the branch is unreachable then).
    try:
        from nats.js.errors import APIError
    except Exception:
        print("  (skipping retry test: nats not installed)")
        return

    def _make_max_msgs_error():
        # Construct a real APIError carrying err_code 10167 ("maximum messages
        # exceeded"), tolerating constructor differences across nats-py versions.
        try:
            return APIError(err_code=10167)
        except TypeError:
            exc = APIError("maximum messages exceeded")
            try:
                exc.err_code = 10167
            except Exception:
                pass
            return exc

    class _Flaky(_FakeJS):
        def __init__(self):
            super().__init__()
            self.failed = False

        async def publish(self, subject, payload):
            if not self.failed and not payload.startswith(EOS_PREFIX):
                self.failed = True
                raise _make_max_msgs_error()
            return await super().publish(subject, payload)

    js = _Flaky()
    sent, *_ = asyncio.run(
        publish_stream(js, "s", lambda i: b"x", num_frames=2, log_every=0,
                       retry_delay_s=0.0)
    )
    assert sent == 2, sent
    assert js.failed, "expected the flaky publish to have raised once"


def test_socket_publish_stream(tmp_path=None):
    import threading

    d = tempfile.mkdtemp(dir=_REPO_TMP)
    fifo = os.path.join(d, "fifo")
    os.mkfifo(fifo)

    received = []

    def reader():
        import struct

        with open(fifo, "rb") as f:
            while True:
                hdr = f.read(4)
                if len(hdr) < 4:
                    break
                (n,) = struct.unpack("!I", hdr)
                received.append(f.read(n))

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    sent, dur, fps = socket_publish_stream(
        fifo, lambda i: f"f{i}".encode(), num_frames=4, rate_hz=0, log_every=0
    )
    t.join(timeout=2)
    assert sent == 4, sent
    assert len(received) == 5, received  # 4 frames + EOS
    assert received[-1].startswith(EOS_PREFIX)
    assert received[-1] == EOS_PREFIX + b"4"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
