# Configuration reference

`pipeline.yaml` is the single source of truth for how the runtime behaves.
Transport type, thread count, batch sizes, stream/subject/durable names, fetch
sizes, and end-of-stream forwarding all come from it. Each example ships its own
`pipeline.yaml`.

## Environment variables the runtime reads

The process that runs a stage (`app.py`) reads only three environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DRAVA_STAGE_CONFIG` | yes | Path to the `pipeline.yaml` to load |
| `DRAVA_STAGE_NAME` | yes | Which `stages:` entry this process is (e.g. `stage1`) |
| `DRAVA_METRICS_FILE` | no | Override `metrics.output_path`; append one JSON record per run here |

Everything else about a stage comes from the entry named `DRAVA_STAGE_NAME`
inside `DRAVA_STAGE_CONFIG`. If no config is loaded, the runtime defaults to the
socket transport. The example benchmark drivers set the two required variables
per stage automatically.

Run a single stage manually:

```shell
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage1
python app.py
```

## Environment variables the publishers read

Publishers are separate data-source processes (not the runtime). They read
`DRAVA_STAGE_CONFIG` for defaults but let a few variables override the YAML:

| Variable | Overrides | Default |
| --- | --- | --- |
| `NATS_URL` | `transport.nats_url` | `nats://0.0.0.0:4222` |
| `DRAVA_STREAM` | stage1 `ingress.stream` | `FRAMES` |
| `DRAVA_SUBJECT` | stage1 `ingress.subject` | `frames.raw` |
| `DRAVA_PUBLISH_RATE_HZ` | `publisher.rate_hz` | `0` (max speed) |
| `DRAVA_PUBLISH_SYNTHETIC` | `publisher.synthetic` | `0` |
| `DRAVA_PUBLISH_NUM_FRAMES` | `publisher.num_frames` | (required) |
| `DRAVA_PUBLISHER_METRICS_FILE` | — | unset (no-op) |

**Precedence:** the runtime uses `pipeline.yaml` only (except `DRAVA_METRICS_FILE`);
publishers use an environment variable if set, otherwise `pipeline.yaml`,
otherwise a built-in default.

## `pipeline.yaml` structure

```yaml
pipeline:
  name: my_pipeline

transport:
  type: nats                    # nats | socket
  nats_url: nats://127.0.0.1:4222

publisher:                      # defaults for the example publishers
  synthetic: true
  num_frames: 10000
  rate_hz: 1000

stages:
  - name: stage1
    runtime:
      threads: 4                # worker threads for this stage
      callback_batch: 256       # frames per callback invocation
      callback_serialize: false # true = one callback at a time
    ingress:
      stream: FRAMES            # NATS stream to read
      subject: frames.raw       # NATS subject to read
      durable: stage1           # durable consumer name
      fetch_batch: 256
      fetch_timeout_ms: 200
    egress:
      stream: PREDICTIONS       # where this stage publishes
      subject: frames.stage1
      # forward_eos defaults to true for non-terminal stages

  - name: stage2
    runtime:
      threads: 4
      callback_batch: 256
    ingress:
      stream: PREDICTIONS
      subject: frames.stage1
      durable: stage2
    egress:
      forward_eos: false        # terminal stage: no downstream
    metrics:
      output_path: /tmp/drava_stage2_metrics.jsonl
```

**Wiring rule:** for a multi-stage pipeline, stage N's `egress`
stream/subject must match stage N+1's `ingress` stream/subject, or no data
flows between them.

## Metrics output

See the [Metrics section of the README](../README.md#metrics) for the fields
recorded per stage. Publishers write a single JSON object to
`DRAVA_PUBLISHER_METRICS_FILE` when set:
`{"frames": N, "duration_s": X, "avg_fps": Y[, "eos_seq": S]}`.
