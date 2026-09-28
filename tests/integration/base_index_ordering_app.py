"""Stage app for the base_index ordering regression test.

Every frame's payload begins with its own 0-based stream position. The
callback recomputes that position as ``base_index + offset_within_batch`` and
compares. If the runtime numbers batches in arrival order, the two always
agree; if it numbers them in task-execution order, they diverge as soon as
callbacks run concurrently.

Prints a single machine-parseable summary line at end of stream:

    [base-index-test] frames=N mismatches=M first_bad=...

This is the invariant that ``drava_frame_batch_t::base_index`` promises and
that stage apps such as examples/ptychonn/app_stage2.py depend on to place a
result at the correct stream position.
"""
import struct
import threading

import drava

SEQ_FMT = "!Q"
SEQ_SIZE = struct.calcsize(SEQ_FMT)

_lock = threading.Lock()
_state = {
    "frames": 0,
    "mismatches": 0,
    "first_bad": None,
    "seen": set(),
    "errors": 0,
}


def func(frames, base_index) -> None:
    local_bad = []
    local_seen = []
    n = len(frames)

    for offset, raw in enumerate(frames):
        if len(raw) < SEQ_SIZE:
            with _lock:
                _state["errors"] += 1
            continue
        (declared,) = struct.unpack_from(SEQ_FMT, raw, 0)
        computed = base_index + offset
        local_seen.append(declared)
        if declared != computed:
            local_bad.append((computed, declared))

    with _lock:
        _state["frames"] += n
        _state["seen"].update(local_seen)
        if local_bad:
            _state["mismatches"] += len(local_bad)
            if _state["first_bad"] is None:
                computed, declared = local_bad[0]
                _state["first_bad"] = f"computed={computed} declared={declared}"


def finalize(expected_frames) -> None:
    with _lock:
        frames = _state["frames"]
        mismatches = _state["mismatches"]
        first_bad = _state["first_bad"] or "none"
        unique = len(_state["seen"])
        errors = _state["errors"]

    expected = int(expected_frames) if expected_frames else frames
    # Every stream position must have been seen exactly once.
    coverage_ok = unique == expected and frames == expected

    drava.log(
        drava.DRAVA_VERBOSE_INFO,
        f"[base-index-test] frames={frames} expected={expected} "
        f"unique={unique} mismatches={mismatches} short_payloads={errors} "
        f"coverage_ok={int(coverage_ok)} first_bad={first_bad}",
    )


drava.run(func, on_end_of_stream=finalize)
