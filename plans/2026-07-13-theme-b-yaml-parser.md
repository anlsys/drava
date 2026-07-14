# Theme B — One YAML schema, one parser + a schema reference

Date: 2026-07-13
Status: Proposed
Impact: High · Effort: M · Local: Yes
Index: [2026-07-13-roadmap.md](2026-07-13-roadmap.md)

## Context

The single `pipeline.yaml` schema is parsed **three** ways:
1. C++ yaml-cpp in [src/drava_internal.cc:117-215](../src/drava_internal.cc#L117).
2. A hand-rolled Python line-parser (`parse_section_value`,
   `parse_stage_ingress_value`, `_parse_yaml_scalar`) copy-pasted across ~5 files.
3. Real PyYAML in `benchmark_two_stages.py` / `tomogan/benchmark.py`.

PyYAML is declared in ptychonn/tomogan `requirements.txt` but **not** in
iris_knn / dataflow / bare_runtime — which is why the brittle hand-rolled parser
exists. There is **no schema reference doc**; valid keys are only discoverable by
reading the C++ source.

## Fix

- Standardize all Python on PyYAML; delete the hand-rolled `_parse_yaml_scalar` /
  `parse_section_value` / `parse_stage_*` cluster. Add `PyYAML` to the missing
  `requirements.txt` files (and add one for bare_runtime).
- Add `docs/pipeline-schema.md` (or a README section) enumerating every key the
  C++ parser reads:
  `transport.{type,nats_url}`,
  `runtime.{threads,callback_batch,callback_flush_timeout_ms,callback_serialize,nats_async_drain_timeout_ms}`,
  `ingress.{stream,subject,durable,socket_path,fetch_batch,fetch_timeout_ms}`,
  `egress.{stream,subject,output_fifo_path,forward_eos}`, `metrics.output_path`.
  Source of truth = [src/drava_internal.cc](../src/drava_internal.cc#L117).

Pairs naturally with Theme C (the shared library is where the single PyYAML-based
config accessor should live).

## Files to modify

- Python: `examples/ptychonn/benchmark.py`, `benchmark_two_stages.py`,
  `examples/tomogan/benchmark.py`, both `publisher_util.py`,
  `examples/bare_runtime/publisher_jetstream.py`.
- `requirements.txt` in iris_knn, dataflow, bare_runtime.
- New `docs/pipeline-schema.md`.

## Verification

- `py_compile` all changed Python.
- Run the shared PyYAML accessor on the example YAMLs and assert values match the
  keys the C++ parser consumes.
