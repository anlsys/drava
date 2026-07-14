# Theme C — De-duplicate examples into a shared library

Date: 2026-07-13
Status: Proposed
Impact: High · Effort: M · Local: Yes
Index: [2026-07-13-roadmap.md](2026-07-13-roadmap.md)

## Context

No shared example library. Across the 3 benchmark scripts (2,007 lines) ~10
helpers are **byte-for-byte identical**: `stream_lines`, `wait_for_log_line`,
`terminate_proc`, `read_metrics_record`, `read_publisher_metrics`, `fmt`,
`tail_text`, `start_nats`, plus the YAML-parse cluster (~64 lines duplicated
between the two ptychonn benchmarks). The two `publisher_util.py` share ~77
identical lines (4 of 6 functions).

A single metrics-format change means editing `read_metrics_record` in 3+ places.
`experiments/_common.py` already has `stream_lines`/`terminate_proc`/`tail_text` —
the maintainers know this pattern; the examples just don't use it.

## Fix

- Create `examples/common/drava_bench.py` (importable) housing shared helpers:
  process streaming (`stream_lines`, `terminate_proc`, `tail_text`,
  `wait_for_log_line`, `start_nats`), metrics readers (`read_metrics_record`,
  `read_publisher_metrics`), YAML access (PyYAML-based — see Theme B), and `fmt`.
  Reuse/merge with `experiments/_common.py` rather than adding a third copy.
- Move `write_publisher_metrics` + config loaders into one shared
  `publisher_common.py`; keep only dataset/payload bits per example.
- Rewrite the 3 benchmarks + 2 `publisher_util.py` to import the shared module.

## Files to modify

- New: `examples/common/drava_bench.py`, `examples/common/publisher_common.py`
  (or extend `experiments/_common.py`).
- `examples/ptychonn/benchmark.py`, `benchmark_two_stages.py`,
  `examples/tomogan/benchmark.py`.
- `examples/ptychonn/publisher_util.py`, `examples/tomogan/publisher_util.py`.

## Verification

- `py_compile` all changed files.
- Extract-and-run the shared readers against sample JSONL/JSON; the round-trip
  tests written in prior work (metrics + publisher metrics) still pass.
