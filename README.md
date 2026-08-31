# Drava

Drava is a C++20 streaming runtime for detector and inference dataflow
pipelines. Frames enter over a transport (NATS JetStream or a Unix socket), are
dispatched in configurable batches to a user callback, and results are published
downstream to the next stage. A stage is just a Python callback plus one call to
`drava.run` — the runtime owns the stream lifecycle (batching, end-of-stream
handling, per-frame indexing, metrics, and optional energy accounting).

Built on the [xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) task runtime, Drava
targets high-throughput scientific pipelines such as ptychography (PtychoNN) and
tomographic denoising (TomoGAN).

## Why Drava

Scientific detector pipelines need to move frames from an instrument through one
or more inference/processing stages at high rate, on HPC hardware. Writing that
plumbing per experiment is repetitive and error-prone. Drava provides it once:

- **Minimal app surface** — a stage is a callback + `drava.run(func)`. The
  runtime handles end-of-stream, batching, multithreaded dispatch, and per-frame
  global indexing, so stage code stays stateless and lock-free.
- **Declarative pipelines** — stages, wiring, thread counts, and batching live in
  a single `pipeline.yaml`; nothing is hardcoded in app code.
- **Pluggable transports** — NATS JetStream or a Unix-domain socket, selected in
  config.
- **Built for measurement** — per-stage throughput, latency, and compute/publish
  breakdown, plus optional exact GPU/CPU energy, are emitted as JSON for
  benchmarks and tuners.
- **HPC-oriented** — built on the xkrt task runtime and a no-GIL Python, so
  callbacks run concurrently across threads on GPU nodes.

## What Drava reports

At end-of-stream each stage emits a metrics record (to the console and, when
configured, to a JSON file). Per-stage fields include:

- **Throughput** — `stage_total_fps`, `rx_item_fps`, `tx_msg_fps`.
- **Latency** — `stage_avg_ms`, `stage_max_ms`.
- **Time breakdown** — `cb_total_s` (callback), `publish_total_s`,
  `compute_total_s` (callback minus publish), `cb_avg_ms`.
- **Counters** — `rx_items`, `rx_bytes`, `tx_msgs`, `tx_bytes`, `cb_batches`.
- **Energy (optional)** — `gpu_energy_j` (NVML), `cpu_energy_j` (RAPL),
  `total_energy_j`, `total_energy_j_per_frame`.

Pipeline-level metrics (end-to-end latency, per-stage throughput, publisher rate)
are assembled by the example benchmark drivers from these per-stage files. See
[Metrics](#metrics) below for the full contract.

## Documentation

| Task | Guide |
|---|---|
| Build the runtime (generic) | [docs/build.md](docs/build.md) |
| Build + run on JLSE (with datasets) | [docs/jlse.md](docs/jlse.md) |
| Run the example applications | [docs/examples.md](docs/examples.md) |
| Write / add / modify an app | [docs/new-app.md](docs/new-app.md) |
| Reproduce the paper experiments | [docs/paper.md](docs/paper.md) |
| Developer CLI (`drava-pipeline`) | [docs/utils.md](docs/utils.md) |

## Quick tour

A stage callback:

```python
import drava

def func(frames, base_index):
    # frames: list[bytes] with the EOS marker already stripped by the runtime
    for raw in frames:
        result = process(raw)
        drava.publish_py(result)     # transform stages publish downstream

drava.run(func)
```

Run a stage (the runtime reads its config from `pipeline.yaml`):

```shell
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage1
python app.py
```

Or run and measure a whole pipeline with an example driver:

```shell
cd examples/ptychonn
python benchmark_two_stages.py --batches 256 --runs 1 --num-frames 10000 \
    --threads 4 --rate-hz 1000 --nats-url nats://127.0.0.1:4222
```

Full walkthroughs, datasets, and transports are in
[docs/examples.md](docs/examples.md) and [docs/jlse.md](docs/jlse.md).

## Example applications

Example applications live in [examples/](examples); each has its own README:

- [PtychoNN](examples/ptychonn) — two-stage ptychographic inference.
- [TomoGAN](examples/tomogan) — tomographic denoising with energy reporting.
- [Bare runtime ceiling](examples/bare_runtime) — runtime message-rate ceiling.
- [Iris KNN](examples/iris_knn) — minimal single-stage inference.
- [Dataflow](examples/dataflow) — minimal transport demo.

Shared helpers and the pipeline launcher live in [examples/common](examples/common).

## Configuration

`pipeline.yaml` is **authoritative for the runtime**: transport type, threads,
callback batching, stream/subject/durable names, fetch sizes, and EOS forwarding
all come from it. The runtime reads only three environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `DRAVA_STAGE_CONFIG` | yes | Path to the `pipeline.yaml` to load. |
| `DRAVA_STAGE_NAME` | yes | Which `stages:` entry this process is (e.g. `stage1`). |
| `DRAVA_METRICS_FILE` | no | Override `metrics.output_path`; append one JSON record per snapshot here. |

If no config is loaded, the runtime defaults to the **socket** transport. The
publishers under `examples/` are separate data-source processes and accept a few
override variables (`NATS_URL`, `DRAVA_STREAM`, `DRAVA_SUBJECT`,
`DRAVA_PUBLISH_*`); env wins, then `pipeline.yaml`, then a built-in default.

## Metrics

At end-of-stream the runtime logs a `[drava-metrics] ...` console line. For
machine consumption, point it at a JSON sink per stage in `pipeline.yaml`:

```yaml
stages:
  - name: stage1
    metrics:
      output_path: /tmp/drava_stage1_metrics.jsonl
```

(or set `DRAVA_METRICS_FILE`, which overrides the YAML value). The runtime then
appends one JSON object per snapshot, keyed by `reason` (`rx_eos`/`tx_eos`) and
`stage`, with the raw counters and derived fields listed in
[What Drava reports](#what-drava-reports). Readers should filter by
`stage`/`reason` and ignore unknown keys so the schema can grow safely.

Publishers write a single-object metrics file when `DRAVA_PUBLISHER_METRICS_FILE`
is set: `{"frames": N, "duration_s": X, "avg_fps": Y[, "eos_seq": S]}`.

**Energy** (optional) is included in the same record from exact hardware counters
over the stage window: `gpu_energy_j` (NVML, Volta+, NVML-enabled build only),
`cpu_energy_j` (Linux RAPL), `total_energy_j`, `total_energy_j_per_frame`.
Unavailable sources are simply omitted. Enable GPU energy by building with NVML
discoverable (`export NVML_ROOT=$CUDA_HOME`).

## Building and tests

- Build the runtime: [docs/build.md](docs/build.md) (generic) or
  [docs/jlse.md](docs/jlse.md) (JLSE, with datasets).
- Pure-Python library/CLI tests (run anywhere):

  ```shell
  python examples/common/tests/run_tests.py
  ```

- C runtime tests (Check + Bats) against a build directory:

  ```shell
  ctest --test-dir build/tests --output-on-failure
  ```

  Setup and transport-specific invocations are in [docs/jlse.md](docs/jlse.md).

## References

- [xkrt / xkaapi task runtime](https://gitlab.inria.fr/xkaapi/dev-v2)
- [NATS C client](https://github.com/nats-io/nats.c/)
- [yaml-cpp](https://github.com/jbeder/yaml-cpp)
