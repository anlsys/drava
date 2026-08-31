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

## Features

- **Minimal app surface** — a stage is a callback + `drava.run(func)`; the
  runtime handles end-of-stream, batching, and per-frame global indexing.
- **Pluggable transports** — NATS JetStream or Unix-domain socket, selected in
  `pipeline.yaml`.
- **Declarative pipelines** — stages, wiring, threads, and batching live in a
  single `pipeline.yaml`.
- **File-based metrics** — per-stage throughput, latency, and compute/publish
  breakdown are written as JSON for benchmarks and tuners.
- **Optional energy accounting** — exact GPU (NVML) and CPU (RAPL) energy
  counters over the stage window, reported per frame.
- **Example apps** — PtychoNN, TomoGAN, Iris KNN, a bare-runtime ceiling, and a
  minimal dataflow example.

## Contents

- [Quickstart](#quickstart)
- [Writing an app](#writing-an-app)
- [Adding a new app](#adding-a-new-app)
- [Configuration](#configuration)
- [Metrics and energy](#metrics-and-energy)
- [Example applications](#example-applications)
- [Building from source](#building-from-source)
- [Tests](#tests)
- [Documentation](#documentation)

## Quickstart

Once Drava is built and importable (see [Building from source](#building-from-source)),
run one of the example pipelines. Each stage is a separate process pointed at its
`pipeline.yaml` via two environment variables; a data-source publisher feeds
stage 1.

Using the NATS JetStream transport (start `nats-server -js` first):

```shell
cd examples/ptychonn

# Terminal 1 — stage 1:
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage1
python app.py

# Terminal 2 — stage 2:
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml DRAVA_STAGE_NAME=stage2
python app_stage2.py

# Terminal 3 — the data source:
python publisher_jetstream.py
```

To run and measure a full multi-stage pipeline in one command, use the example
benchmark driver, which manages NATS, wires the stages, and reports throughput:

```shell
cd examples/ptychonn
python benchmark_two_stages.py --batches 256 --runs 1 --num-frames 10000 \
    --threads 4 --rate-hz 1000 --nats-url nats://127.0.0.1:4222
```

An optional [`drava-pipeline`](docs/utils.md) helper can validate, scaffold, and
launch all stages with a single command.

## Writing an app

A Drava stage is a callback plus one call to `drava.run`. The runtime strips the
end-of-stream (EOS) marker before your callback runs, tracks each frame's global
position, drives finalization once the stream drains, and forwards EOS to the
next stage — so the callback only handles data:

```python
import drava

def func(frames, base_index):
    # frames: list[bytes] of data payloads (no EOS marker)
    # base_index: global index of frames[0] across the whole stream
    for i, raw in enumerate(frames):
        result = process(raw)
        drava.publish_py(result)   # transform stages publish downstream

drava.run(func)
```

- Callbacks may be written as `func(frames)` or `func(frames, base_index)`;
  `drava.run` adapts either.
- For a **terminal** stage that produces a final result, pass an
  `on_end_of_stream` hook and set `egress.forward_eos: false` in the pipeline
  config:

  ```python
  def finalize(expected_frames):
      write_output()          # runs once, after all callbacks drain

  drava.run(func, on_end_of_stream=finalize)
  ```

- Concurrency: with `callback_serialize: false` the runtime runs callbacks on
  multiple threads. Because the runtime owns EOS accounting and `base_index`, a
  stateless callback needs no lock. Keep app-side locks only for state the app
  itself accumulates (e.g. a result list).
- Knobs (`threads`, `callback_batch`, `callback_serialize`, `forward_eos`) live
  in the stage's `pipeline.yaml`, not in app code.

## Adding a new app

A new app needs only a **stage callback** (`app.py`) and a **`pipeline.yaml`**;
everything generic (config parsing, the publisher loop, EOS, metrics) comes from
[examples/common](examples/common). The quickest start is to copy an existing
example directory (`examples/iris_knn` for one stage, `examples/ptychonn` for
two) and adapt it.

1. **Write the callback** in `app.py` (see [Writing an app](#writing-an-app)).
   A terminal stage uses an `on_end_of_stream` hook and `egress.forward_eos: false`.

2. **Write `pipeline.yaml`** — set `transport.type`, each stage's
   `runtime.threads` / `callback_batch`, and the `ingress`/`egress`
   stream/subject names. For a multi-stage pipeline, **stage N's `egress` must
   match stage N+1's `ingress`**.

3. **Add a publisher** — the data source is the only app-specific part. Reuse the
   shared loop from `drava_common`:

   ```python
   import asyncio, os, sys
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
   from drava_common import (connect_jetstream, load_transport_config,
                             load_publish_config, publish_stream)

   def make_payload(i: int) -> bytes:
       ...                                  # your bytes for frame i

   async def main():
       url, stream, subject = load_transport_config()
       rate_hz, synthetic, num_frames = load_publish_config()
       js = await connect_jetstream(url, stream, subject)
       await publish_stream(js, subject, make_payload, num_frames, rate_hz=rate_hz)

   asyncio.run(main())
   ```

   For the socket transport, use `socket_publish_stream` (see
   `examples/ptychonn/publisher_socket.py`).

4. **Run it** as in [Quickstart](#quickstart) (one process per stage plus the
   publisher), or with the [`drava-pipeline`](docs/utils.md) helper.

Conventions the runtime relies on:

- The app callback must **not** parse the `DRAVA_EOS:` marker — the runtime owns
  EOS. Publishers (the data source) still emit it; `publish_stream` does this.
- Keep example-specific code minimal (payload source + callback). Put shared
  helpers in `drava_common`, not per-example copies.
- Retired or unused code files go in an `archive/` subfolder of the example.

## Configuration

`pipeline.yaml` is **authoritative for the runtime**. Transport type, thread
count, callback batching, stream/subject/durable names, fetch sizes, and EOS
forwarding are all read from the YAML stage config — not from environment
variables. Each example ships its own `pipeline.yaml`.

### Environment variables the runtime reads

The runtime (the process that imports `drava` / runs `app.py`) reads only three
environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `DRAVA_STAGE_CONFIG` | yes | Path to the `pipeline.yaml` to load. |
| `DRAVA_STAGE_NAME` | yes | Which `stages:` entry this process is (e.g. `stage1`). |
| `DRAVA_METRICS_FILE` | no | Override `metrics.output_path`; append one JSON record per snapshot here. |

Everything else about the stage (transport, threads, streams, batching) comes
from the stage named `DRAVA_STAGE_NAME` inside `DRAVA_STAGE_CONFIG`. If no config
is loaded, the runtime defaults to the **socket** transport. The benchmark
drivers (and the [`drava-pipeline`](docs/utils.md) helper) set these two required
variables per stage automatically.

### Environment variables the publishers read

The publishers under `examples/` are separate data-source processes (not the
runtime). They read `DRAVA_STAGE_CONFIG` for defaults but let a few env vars
**override** the YAML:

| Variable | Overrides YAML | Default |
|---|---|---|
| `NATS_URL` | `transport.nats_url` | `nats://0.0.0.0:4222` |
| `DRAVA_STREAM` | stage1 `ingress.stream` | `FRAMES` |
| `DRAVA_SUBJECT` | stage1 `ingress.subject` | `frames.raw` |
| `DRAVA_PUBLISH_RATE_HZ` | `publisher.rate_hz` | `0` |
| `DRAVA_PUBLISH_SYNTHETIC` | `publisher.synthetic` | `0` |
| `DRAVA_PUBLISH_NUM_FRAMES` | `publisher.num_frames` | (required) |
| `DRAVA_PUBLISHER_METRICS_FILE` | — | unset (no-op) |

**Precedence:** the runtime uses `pipeline.yaml` only (except `DRAVA_METRICS_FILE`);
publishers use an env var if set, otherwise `pipeline.yaml`, otherwise a built-in
default.

## Metrics and energy

At end-of-stream the runtime logs a human-readable `[drava-metrics] ...` line to
the console. For machine consumption, point the runtime at a structured JSON sink
per stage in `pipeline.yaml`:

```yaml
stages:
  - name: stage1
    metrics:
      output_path: /tmp/drava_stage1_metrics.jsonl
```

or via `DRAVA_METRICS_FILE` (which overrides the YAML value). The runtime then
**appends one JSON object per metrics snapshot**. Each record carries `reason`
(`rx_eos`/`tx_eos`), `stage`, raw counters (`rx_items`, `tx_msgs`, `cb_batches`,
…), and derived fields (`stage_total_s`, `stage_total_fps`, `cb_avg_ms`,
`compute_total_s`, `publish_total_s`, …). Readers should filter by
`stage`/`reason` and ignore unknown keys, so the schema can grow safely.

Publishers are separate processes, so each writes its own single-object metrics
file when `DRAVA_PUBLISHER_METRICS_FILE` is set:
`{"frames": N, "duration_s": X, "avg_fps": Y[, "eos_seq": S]}`.

**Energy** (optional) is reported in the same record, from exact hardware
counters over the stage window: `gpu_energy_j` (NVML, Volta+, NVML-enabled build
only), `cpu_energy_j` (Linux RAPL powercap sysfs), plus `total_energy_j` and
`total_energy_j_per_frame`. Fields whose source is unavailable are omitted. To
enable GPU energy, build with NVML discoverable (`export NVML_ROOT=$CUDA_HOME`).

## Example applications

Example applications live in the [examples](examples) directory; each has its own
README:

- [PtychoNN](examples/ptychonn) — two-stage ptychographic inference.
- [TomoGAN](examples/tomogan) — tomographic denoising with energy reporting.
- [Bare runtime ceiling](examples/bare_runtime) — runtime message-rate ceiling.
- [Iris KNN](examples/iris_knn) — minimal single-stage inference.
- [Dataflow](examples/dataflow) — minimal transport demo.

Shared helpers and the pipeline launcher live in [examples/common](examples/common).

## Building from source

> The C++ runtime depends on [xkrt](https://gitlab.inria.fr/xkaapi/dev-v2),
> yaml-cpp, optionally NATS (nats.c) and NVML/CUDA, and a no-GIL Python (3.13+
> built with `--disable-gil`). It has been developed and tested on the ALCF
> **JLSE** cluster; for the exact, preconfigured build there, see
> **[docs/jlse.md](docs/jlse.md)**. The example apps and the `drava-pipeline`
> CLI are pure Python and run anywhere.

### Dependencies

- A C/C++ compiler with C++20 support (tested with LLVM/Clang).
- [xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) task runtime.
- [yaml-cpp](https://github.com/jbeder/yaml-cpp).
- SWIG (for the Python bindings).
- A no-GIL Python build (3.13+ with `--disable-gil`).
- Optional: NATS server + [nats.c](https://github.com/nats-io/nats.c) client for
  the JetStream transport; NVML/CUDA for GPU energy.

### Build

With the dependencies available (see [docs/jlse.md](docs/jlse.md) for building
yaml-cpp / NATS and the module setup on JLSE):

```shell
export NATS_ROOT=/path/to/nats     # only for the JetStream transport
export NVML_ROOT=$CUDA_HOME        # only for GPU energy
mkdir build && cd build
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH"   # so `import drava` finds the built module
```

CMake prints whether the NATS and NVML backends were enabled.

## Tests

The pure-Python library and CLI tests run anywhere (no runtime build needed):

```shell
python examples/common/tests/run_tests.py
```

The C runtime tests use [Check](https://libcheck.github.io/check/) and
[Bats](https://bats-core.readthedocs.io/) and run against a build directory:

```shell
ctest --test-dir build/tests --output-on-failure
```

Setup and transport-specific/integration test invocations are in
[docs/jlse.md](docs/jlse.md).

## Documentation

- [docs/jlse.md](docs/jlse.md) — building on the JLSE cluster (exact module and
  dependency paths).
- [docs/paper.md](docs/paper.md) — reproducing the paper experiments and
  benchmarks.
- [docs/utils.md](docs/utils.md) — the optional `drava-pipeline` developer CLI.

## References

- [xkrt / xkaapi task runtime](https://gitlab.inria.fr/xkaapi/dev-v2)
- [NATS C client](https://github.com/nats-io/nats.c/)
- [yaml-cpp](https://github.com/jbeder/yaml-cpp)
