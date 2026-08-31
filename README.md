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
- [Adding a new example app](#adding-a-new-example-app)
- [Configuration](#configuration)
- [Metrics and energy](#metrics-and-energy)
- [Example applications](#example-applications)
- [Building from source](#building-from-source)
- [Tests](#tests)
- [Paper experiments](#paper-experiments)
- [Developer utilities](#developer-utilities)

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

See each example's README for details, and
[Developer utilities](#developer-utilities) for an optional launcher/scaffolder.

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

## Adding a new example app

A new app needs only a **stage callback** (`app.py`) and a **`pipeline.yaml`**;
everything generic (config parsing, the publisher loop, EOS, metrics) comes from
[examples/common](examples/common). The quickest starting point is to copy an
existing example directory (e.g. `examples/iris_knn` for a single stage, or
`examples/ptychonn` for two stages) and adapt it.

1. **Write the callback** in `app.py`. It receives a batch of raw payloads; the
   runtime already stripped EOS and assigns `base_index`:

   ```python
   import drava

   def func(frames, base_index):
       for raw in frames:
           result = process(raw)          # your decode + compute
           drava.publish_py(result)       # transform stages publish downstream
   drava.run(func)
   ```

   For a **terminal** stage, use an `on_end_of_stream` hook and set
   `egress.forward_eos: false` in `pipeline.yaml`.

2. **Write `pipeline.yaml`** — set `transport.type`, each stage's
   `runtime.threads` / `callback_batch`, and the `ingress`/`egress`
   stream/subject names. For a multi-stage pipeline, **stage N's `egress` must
   match stage N+1's `ingress`**.

3. **Add a publisher** (the data source is the only app-specific part). Reuse the
   shared loop from `drava_common`:

   ```python
   # examples/myapp/publisher_jetstream.py
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

   For the socket transport, use `socket_publish_stream` instead (see
   `examples/ptychonn/publisher_socket.py`).

4. **Run it** as shown in [Quickstart](#quickstart) (one process per stage plus
   the publisher). The optional [`drava-pipeline`](#developer-utilities) helper
   can scaffold, validate, and launch all stages with one command.

Conventions the runtime relies on:

- The app callback must **not** parse the `DRAVA_EOS:` marker — the runtime owns
  EOS. Publishers (the data source) still emit it; `publish_stream` does this.
- Keep example-specific code minimal (payload source + the callback). Put shared
  helpers in `drava_common`, not per-example copies.
- Retired or unused code files go in an `archive/` subfolder of the example,
  rather than being deleted.

## Configuration

`pipeline.yaml` is **authoritative for the runtime**. Transport type, thread
count, callback batching, stream/subject/durable names, fetch sizes, and EOS
forwarding are all read from the YAML stage config — not from environment
variables. Each example ships its own `pipeline.yaml`; edit that file to change
runtime behavior.

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
drivers (and the optional [`drava-pipeline`](#developer-utilities) helper) set
these two required variables for each stage automatically.

Running a single stage manually:

```shell
export DRAVA_STAGE_CONFIG=$PWD/pipeline.yaml
export DRAVA_STAGE_NAME=stage1
python app.py
```

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

### Precedence summary

| Consumer | Source of truth |
|---|---|
| Runtime (`app.py`) | `pipeline.yaml` only, except `DRAVA_METRICS_FILE` overrides `metrics.output_path`. |
| Publishers | env var if set, otherwise `pipeline.yaml`, otherwise built-in default. |

## Metrics and energy

At end-of-stream the runtime logs a human-readable `[drava-metrics] ...` line to
the console. For machine consumption (benchmarks, tuners), point the runtime at
a structured sink instead of scraping that log line:

- Per stage in `pipeline.yaml`:

  ```yaml
  stages:
    - name: stage1
      metrics:
        output_path: /tmp/drava_stage1_metrics.jsonl
  ```

- Or via environment variable (overrides the YAML value):

  ```shell
  export DRAVA_METRICS_FILE=/tmp/drava_metrics.jsonl
  ```

When set, the runtime **appends one JSON object per metrics snapshot** to that
file. Each record carries `reason` (`rx_eos`/`tx_eos`), `stage`, the raw counters
(`rx_items`, `tx_msgs`, `cb_batches`, …), and the derived fields
(`stage_total_s`, `stage_total_fps`, `cb_avg_ms`, `compute_total_s`,
`publish_total_s`, …). Readers should filter by `stage`/`reason` and ignore
unknown keys, so the schema can grow without breaking consumers.

### Publisher metrics

The publishers are separate data-source processes (plain NATS/socket clients that
do not link the runtime), so their throughput is not visible to the runtime. Each
publisher reports its own metrics to a file instead of only to stdout:

```shell
export DRAVA_PUBLISHER_METRICS_FILE=/tmp/drava_pub_metrics.json
```

When set, the publisher writes a **single JSON object** at completion:
`{"frames": N, "duration_s": X, "avg_fps": Y[, "eos_seq": S]}`.

### Energy

When available, the runtime reports **energy** in the same metrics record,
measured from hardware counters over the runtime's stage window (first frame to
end-of-stream) — not sampled and integrated in Python:

- `gpu_energy_j` — GPU energy from NVML's `nvmlDeviceGetTotalEnergyConsumption`
  (a monotonic counter, Volta+). Present only in an NVML-enabled build.
- `cpu_energy_j` — CPU package energy from the Linux RAPL powercap sysfs
  (`/sys/class/powercap/intel-rapl:*`), when the domains are readable.
- `total_energy_j`, `total_energy_j_per_frame` — sum of the available sources.

Any field whose source is unavailable is simply omitted, so consumers treat
these as optional. To enable GPU energy, build with NVML discoverable (NVML ships
with the CUDA toolkit/driver):

```shell
export NVML_ROOT=$CUDA_HOME        # or e.g. /usr/local/cuda
# then configure/build as usual; CMake prints whether NVML was enabled.
```

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
> **JLSE** cluster, where these dependencies are preinstalled; building elsewhere
> requires providing them yourself. The example apps and the `drava-pipeline`
> CLI are pure Python and run anywhere.

### Dependencies

- A C/C++ compiler with C++20 support (tested with LLVM/Clang).
- [xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) task runtime.
- [yaml-cpp](https://github.com/jbeder/yaml-cpp).
- SWIG (for the Python bindings).
- A no-GIL Python build (3.13+ with `--disable-gil`).
- Optional: NATS server + [nats.c](https://github.com/nats-io/nats.c) client for
  the JetStream transport; NVML/CUDA for GPU energy.

<details>
<summary>Example environment setup on JLSE (module load)</summary>

```shell
module use /soft/modulefiles
module load spack/gcc-0.6.1
module use <shared-modules-path>            # site-provided xkaapi modules

module load llvm/master-nightly cmake intel/oneapi/release/2024.1 cuda/12.3.0 hwloc
module load xkaapi/<version>/Debug-cuda     # for A40/A100/H100 nodes
module load swig/4.4.1
module load python/3.14.3-no-gil
```
</details>

### Build yaml-cpp

```shell
git clone https://github.com/jbeder/yaml-cpp.git
cd yaml-cpp && mkdir build && cd build
CC=clang CXX=clang++ cmake .. -DYAML_BUILD_SHARED_LIBS=ON \
    -DCMAKE_INSTALL_PREFIX=$HOME/opt/yaml-cpp-install
make -j && make install
```

### (Optional) NATS for the JetStream transport

```shell
# NATS server
curl -fsSL https://binaries.nats.dev/nats-io/nats-server/v2@v2.11.6 | sh

# NATS C client
git clone https://github.com/nats-io/nats.c.git
cd nats.c && mkdir build && cd build
cmake .. -DNATS_BUILD_STREAMING=OFF -DCMAKE_INSTALL_PREFIX=$HOME/opt/nats
make -j && make install
```

### Build Drava

```shell
export NATS_ROOT=$HOME/opt/nats     # only if using the JetStream transport
export NVML_ROOT=$CUDA_HOME         # only if you want GPU energy
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
[Bats](https://bats-core.readthedocs.io/); they run against a build directory:

```shell
ctest --test-dir build/tests --output-on-failure

# Transport-specific tests (opt-in; require a running server/endpoint):
USE_NATS=1  ctest --test-dir build/tests -R transport_nats -V
USE_SOCKET=1 ctest --test-dir build/tests -R transport_socket -V

# Python integration tests:
ctest --test-dir build/tests -R integration_transport_jetstream_python -V
ctest --test-dir build/tests -R integration_transport_socket_python -V
```

Point `CHECK_ROOT` / `NATS_ROOT` at your installs and put `nats-server` and
`bats` on `PATH` before running the C tests.

## Paper experiments

The submitted-paper experiment index is in [experiments.md](experiments.md).
Experiment drivers, preserved logs, result CSVs, and figure-generation packages
are organized under [experiments](experiments); final figures are in
[figs/paper_figs](figs/paper_figs).

## Developer utilities

`drava-pipeline` is an optional convenience CLI (in
[examples/common](examples/common)) for working with pipelines during
development — it is **not** required to run apps or reproduce the paper
experiments (those use the manual flow and the example benchmark drivers). It
validates a `pipeline.yaml`, scaffolds a new app, and launches every stage with
the right `DRAVA_STAGE_NAME` wired automatically.

Run the `drava-pipeline` script at the repo root; it self-bootstraps, so no
install and no `PYTHONPATH` are needed:

```shell
# Validate stage wiring (egress of stage N must match ingress of stage N+1):
./drava-pipeline validate examples/ptychonn/pipeline.yaml

# Scaffold a new app + pipeline.yaml (adds app_stageN.py for extra stages):
./drava-pipeline new-app myapp --stages 2

# Launch all stages (downstream first) plus the publisher, managing NATS for you:
./drava-pipeline run examples/ptychonn/pipeline.yaml \
    --start-nats \
    --publisher "python publisher_jetstream.py"
```

For the NATS transport, `run` verifies a server is reachable before launching
stages (they abort on connect failure); `--start-nats` runs and stops
`nats-server -js` for you (customize with `--nats-command` / `--nats-config`).

## References

- [xkrt / xkaapi task runtime](https://gitlab.inria.fr/xkaapi/dev-v2)
- [NATS C client](https://github.com/nats-io/nats.c/)
- [yaml-cpp](https://github.com/jbeder/yaml-cpp)
