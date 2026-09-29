# SystemFlow interface

[SystemFlow](https://github.com/wilkieolin/system_flow) is a performance-modeling
framework for scientific data-processing systems. Drava can read a SystemFlow
**model document** and derive its initial `pipeline.yaml` from it, so the
pipeline you run is traceable to the performance model that motivated it.

The interface is currently **one-way and read-only**: Drava reads SystemFlow,
never the reverse. Pushing measured benchmark data back into SystemFlow to
refine the model is a planned second phase (see [Roadmap](#roadmap)).

For copy-paste commands on the cluster, see
[systemflow-jlse.md](systemflow-jlse.md).

## Status

| Capability | State |
|---|---|
| Read a SystemFlow model document → `pipeline.yaml` | Implemented |
| Linear (chain) pipelines | Supported |
| Branching / fan-in pipelines | Rejected with a clear error |
| Push measured benchmarks back to SystemFlow | Not implemented (phase 2) |

## Quick start

```shell
# Print the derived pipeline.yaml
./drava-pipeline from-systemflow examples/ptychopinn/systemflow_model.yaml

# Write it out (refuses to clobber without --force)
./drava-pipeline from-systemflow examples/ptychopinn/systemflow_model.yaml \
    -o examples/ptychopinn/pipeline.yaml --force

# Pick a graph when the document defines several
./drava-pipeline from-systemflow model.yaml --graph "ptychopinn inference"
```

The generated config is validated (the same checks as `drava-pipeline validate`)
before anything is written, and can be run directly:

```shell
./drava-pipeline run examples/ptychopinn/pipeline.yaml --start-nats
```

From Python:

```python
from drava_common import import_systemflow_pipeline, validate_pipeline

mapping, cfg = import_systemflow_pipeline("systemflow_model.yaml")
warnings = validate_pipeline(cfg)
```

## `systemflow` is an optional dependency

A SystemFlow model document is plain YAML, so the importer does **not** require
the `systemflow` package. When SystemFlow *is* installed, Drava reuses its YAML
loader; otherwise it uses an equivalent loader defined locally.

This matters for one specific reason: SystemFlow patches PyYAML's float resolver
(`systemflow/io/loader.py:27`) so unsigned-exponent literals like `40e6` parse as
floats. Stock `yaml.safe_load` returns the **string** `"40e6"`. Drava replicates
that resolver so a document reads identically either way. Do not parse a model
document with a bare `yaml.safe_load`.

## How the mapping works

### Topology

The chosen graph must be a **linear chain** — each node with at most one
predecessor and one successor. Chain order becomes stage order:

```
SystemFlow node[0] ──link──> node[1] ──link──> node[2]
        │                      │                 │
      stage1                 stage2            stage3
```

Fan-out, fan-in, cycles, and disconnected nodes are rejected rather than guessed
at, because a Drava stage takes exactly one ingress.

Each SystemFlow **link is one Drava stream**: it supplies the upstream
`egress.{stream,subject}` *and* the downstream `ingress.{stream,subject}`. That
is what makes `validate_pipeline()` pass by construction — the classic
"egress/ingress typo, nothing is flowing" bug cannot be expressed.

### Explicit, not inferred

Drava runtime knobs are read **only** where the model document states them
outright, in parameters prefixed `drava `. Thread counts and batch sizes are
never derived from SystemFlow's FLOP or energy estimates — that would be
inventing physics from numbers that do not describe it. An unrecognized
`drava ...` parameter is an error, so typos fail loudly instead of being
silently dropped.

### One document, two readers

The same file is safe for both projects:

- SystemFlow's `parse_document` (`systemflow/io/schema.py:105`) ignores unknown
  top-level keys, so the `drava:` section does not break SystemFlow. Its
  `Component` (`systemflow/node.py:288`) tolerates extra parameters, so the
  `"drava ..."` keys do not break it either.
- Drava's C++ reader (`src/drava_internal.cc:117`) reads only `transport` and
  `stages`, so the `systemflow:` provenance block written into `pipeline.yaml`
  is ignored by the runtime.

## Model document reference

Top-level `drava:` section — all keys optional:

```yaml
drava:
  pipeline_name: my_pipeline          # else the document `name`, else graph name
  transport:
    type: nats                        # nats | socket   (default: nats)
    nats_url: nats://127.0.0.1:4222
  source:                             # ingress of the first stage
    stream: FRAMES
    subject: frames.raw
  durable_prefix: drava               # durables become <prefix>_<pipeline>_<stage>
  publisher: {...}                    # copied verbatim into pipeline.yaml
  benchmark: {...}                    # copied verbatim into pipeline.yaml
```

Node parameters — all optional:

| Parameter | Maps to |
|---|---|
| `"drava stage (str)"` | stage name (default `stage1`…`stageN`) |
| `"drava threads (n)"` | `runtime.threads` |
| `"drava callback batch (n)"` | `runtime.callback_batch` |
| `"drava callback flush timeout (ms)"` | `runtime.callback_flush_timeout_ms` |
| `"drava callback serialize (bool)"` | `runtime.callback_serialize` |
| `"drava nats async drain timeout (ms)"` | `runtime.nats_async_drain_timeout_ms` |
| `"drava ingress durable (str)"` | `ingress.durable` |
| `"drava ingress socket path (str)"` | `ingress.socket_path` |
| `"drava fetch batch (n)"` | `ingress.fetch_batch` |
| `"drava fetch timeout (ms)"` | `ingress.fetch_timeout_ms` |
| `"drava egress output fifo path (str)"` | `egress.output_fifo_path` |
| `"drava forward eos (bool)"` | `egress.forward_eos` |
| `"drava metrics output path (str)"` | `metrics.output_path` |

Link parameters — all optional:

| Parameter | Maps to |
|---|---|
| `"drava stream (str)"` | the NATS stream carrying this link |
| `"drava subject (str)"` | the NATS subject carrying this link |

Defaults applied by the importer: the first stage's ingress falls back to
`FRAMES` / `frames.raw` on NATS; a link with no explicit stream/subject gets the
upper-cased link name and `frames.<upstream stage>`; the terminal stage gets
`egress.forward_eos: false`.

## Provenance

Every generated `pipeline.yaml` carries the block that ties each stage back to
its SystemFlow node:

```yaml
systemflow:
  schema_version: '1.0'
  model_name: PtychoPINN two-stage inference pipeline
  model_path: examples/ptychopinn/systemflow_model.yaml
  graph: ptychopinn inference
  imported_by: drava_common.systemflow v1
  stage_nodes:
    stage1: PtychoPINN inference
    stage2: Canvas assembly
```

`stage_nodes` is the attribution map phase 2 needs to send a measurement taken
on `stage1` back to the right SystemFlow node.

## Worked example: PtychoPINN

[examples/ptychopinn/systemflow_model.yaml](../examples/ptychopinn/systemflow_model.yaml)
models the two-stage PtychoPINN pipeline and regenerates the checked-in
`examples/ptychopinn/pipeline.yaml` exactly. A unit test
(`examples/common/tests/test_systemflow.py`) asserts that equivalence, so the
model and the config cannot silently drift apart.

That document shows the intended split: SystemFlow-side cost parameters
(`"overlap (%)"`, `"xy images (n,n)"`, `"disk storage rate (B/s)"`) sit beside
Drava-side runtime knobs (`"drava threads (n)"`, `"drava callback batch (n)"`) in
the same node, each ignored by the other project.

## Roadmap

Phase 2 — pushing measured benchmark data back into SystemFlow via
`systemflow.io.calibrate` to refine the model after real Drava runs — is **not
implemented**. When it lands it must write to a Drava-owned output path and
never modify a SystemFlow checkout.

## Tests

```shell
python examples/common/tests/test_systemflow.py
```

Pure Python; runs anywhere, no runtime build and no `systemflow` install needed.
The SystemFlow-schema conformance test is skipped automatically when a
`system_flow/` checkout is not present next to this repo.

For the cluster procedure — including an end-to-end A/B run of PtychoPINN
against the derived config — see [systemflow-jlse.md](systemflow-jlse.md).
