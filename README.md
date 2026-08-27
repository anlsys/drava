# Drava
Runtime and end-to-end simulation for BIA systems and simulations

## Installation

### Requirements
- C/C++ compiler with C++20 support (tested: LLVM ≥ 20.x)
- xkrt - https://gitlab.inria.fr/xkaapi/dev-v2 (see [JLSE](#on-jlse))
- swig if generating Python bindings
- NATS server if run with Jetstream

### On JLSE
Requirements are preinstalled:

```shell
# GPU 

# module path setup
module use /soft/modulefiles
module load spack/gcc-0.6.1
module use /home/rpereira/shared/modules

# C/C++ 20 compiler
module load llvm/master-nightly
module load cmake
module load intel/oneapi/release/2024.1
module load cuda/12.3.0
module load hwloc

# XKRT
module load xkaapi/502226c375a8/Debug-cuda  #  if using A40/A100/H100 nodes

# if using swig
module load swig/4.4.1

# if using python 3.14.3, compiled with `--disable-gil`
module load python/3.14.3-no-gil
```

### YAML CPP requirements
- Build YAML CPP 
```shell
git clone git@github.com:jbeder/yaml-cpp.git
mkdir build && cd build
CC=clang CXX=clang++ cmake .. -DYAML_BUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=$HOME/opt/yaml-cpp-install
make -j
make install
```

### (Optional) NATS requirements
- Install NATS server
```shell
cd ~/nats_binary
curl -fsSL https://binaries.nats.dev/nats-io/nats-server/v2@v2.11.6 | sh
```
- Build NATS C client
```shell
git clone git@github.com:nats-io/nats.c.git
mkdir build && cd build
cmake .. -DNATS_BUILD_STREAMING=OFF -DCMAKE_INSTALL_PREFIX=$HOME/opt/nats
make -j
make install
```

### Build Drava
```shell
# Define NATS_ROOT if Jetstream is used
export NATS_ROOT=$HOME/opt/nats
mkdir build-debug-nats && cd build-debug-nats
CC=clang CXX=clang++ cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j
export PYTHONPATH="$(pwd):$PYTHONPATH" # so that the build dir is in the Python path
```

## Configuration

`pipeline.yaml` is **authoritative for the runtime**. Transport type, thread
count, callback batching, stream/subject/durable names, fetch sizes, and EOS
forwarding are all read from the YAML stage config — not from environment
variables. Each example ships its own `pipeline.yaml`; edit that file to change
runtime behavior.

### Environment variables the runtime actually reads

The runtime (the process that imports `drava` / runs `app.py`) reads only three
environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `DRAVA_STAGE_CONFIG` | yes | Absolute path to the `pipeline.yaml` to load. |
| `DRAVA_STAGE_NAME` | yes | Which `stages:` entry this process is (e.g. `stage1`). |
| `DRAVA_METRICS_FILE` | no | Override `metrics.output_path`; append one JSON record per snapshot here. |

Everything else about the stage (transport, threads, streams, batching) comes
from the stage named `DRAVA_STAGE_NAME` inside `DRAVA_STAGE_CONFIG`. If the
config is not loaded, the runtime defaults to the **socket** transport.

> Note: older docs referenced `DRAVA_TRANSPORT`, `DRAVA_THREADS`,
> `DRAVA_STREAM`, `DRAVA_SUBJECT`, `DRAVA_DURABLE`, `DRAVA_INFER_BATCH`, etc. for
> the runtime. **The runtime does not read those.** Set the equivalents in
> `pipeline.yaml` instead (`transport.type`, `runtime.threads`,
> `ingress.stream`, `ingress.subject`, `ingress.durable`, `runtime.callback_batch`).

Running a stage manually (the benchmark drivers set these for you):

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

## Applications

Example applications are located in [examples](examples) directory.
Each application contains its own README with instructions for running it.
Available applications:
- [PtychoNN](examples/ptychonn)
- [TomoGAN](examples/tomogan)
- [Bare runtime ceiling](examples/bare_runtime)
- [Iris Inference](examples/iris_knn)
- [Dataflow](examples/dataflow)

Shared helpers and a pipeline launcher live in
[examples/common](examples/common).

### Running a pipeline

The `drava-pipeline` CLI validates a `pipeline.yaml` and launches every stage
with the right `DRAVA_STAGE_NAME` wired automatically — no need to open one
terminal per stage. Run the `drava-pipeline` script at the repo root; it
self-bootstraps (no `pip install`, no `PYTHONPATH`):

```shell
# Validate stage wiring (egress of stage N must match ingress of stage N+1):
./drava-pipeline validate examples/ptychonn/pipeline.yaml

# Launch all stages (downstream first); optionally launch the publisher too.
# For the NATS transport, a server must be reachable; --start-nats runs and
# stops one for you (otherwise start `nats-server -js` yourself first):
./drava-pipeline run examples/ptychonn/pipeline.yaml \
    --start-nats \
    --publisher "python publisher_jetstream.py"

# Scaffold a new example app + pipeline.yaml:
./drava-pipeline new-app myapp --stages 2
```

For the NATS transport the launcher checks that a server is reachable before
launching stages (they abort on connect failure) and prints a clear message if
not. `--start-nats` starts `nats-server -js` (override the binary with
`--nats-command`, or pass a config with `--nats-config`) and stops it on exit.

### Writing an app

A Drava stage is just a callback plus one call to `drava.run`. The runtime owns
the stream lifecycle — it strips the end-of-stream (EOS) marker before your
callback runs, tracks each frame's global position, drives finalization once the
stream drains, and forwards EOS to the next stage — so the callback only handles
data:

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

### Adding a new example app

A new app needs only a **stage callback** (`app.py`) and a **`pipeline.yaml`**;
everything generic (config parsing, the publisher loop, EOS, metrics, launching)
comes from [examples/common](examples/common). Steps:

1. **Scaffold** the skeleton (creates `pipeline.yaml` + `app.py`, and
   `app_stageN.py` for extra stages):

   ```shell
   ./drava-pipeline new-app myapp --stages 1     # or --stages 2 for a pipeline
   # creates examples/myapp/
   ```

2. **Write the callback** in `app.py`. It receives a batch of raw payloads; the
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
   `egress.forward_eos: false` (the scaffolder does this for the last stage).

3. **Edit `pipeline.yaml`** — set `transport.type`, each stage's
   `runtime.threads` / `callback_batch`, and the `ingress`/`egress`
   stream/subject names. For a multi-stage pipeline, **stage N's `egress` must
   match stage N+1's `ingress`** (the launcher validates this).

4. **Add a publisher** (the data source is the only app-specific publisher part).
   Reuse the shared loop from `drava_common`:

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

5. **Validate and run:**

   ```shell
   ./drava-pipeline validate examples/myapp/pipeline.yaml
   ./drava-pipeline run examples/myapp/pipeline.yaml --start-nats \
       --publisher "python publisher_jetstream.py"
   ```

Conventions the runtime relies on (don't regress):
- The app callback must **not** parse the `DRAVA_EOS:` marker — the runtime owns
  EOS. Publishers (the data source) still emit it; `publish_stream` does this.
- Keep example-specific code minimal (payload source + the callback). Put shared
  helpers in `drava_common`, not per-example copies.
- Generated outputs (`bench_logs*/`, `drava_output/`, `aggregate.csv`, result
  HDF5/PNGs) are git-ignored; don't commit them. Retired/unused files go in an
  `archive/` subfolder of the example.

### Runtime metrics

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
file. Each record carries `reason` (`rx_eos`/`tx_eos`), `stage`, the raw
counters (`rx_items`, `tx_msgs`, `cb_batches`, …), and the derived fields
(`stage_total_s`, `stage_total_fps`, `cb_avg_ms`, `compute_total_s`,
`publish_total_s`, …) — the same values as the console line. Readers should
filter by `stage`/`reason` and ignore unknown keys, so the schema can grow
without breaking consumers. The benchmark drivers under `examples/` read this
file; they no longer parse the console output.

#### Publisher metrics

The publishers under `examples/` are separate data-source processes (plain
NATS/socket clients — they do not link the runtime), so their throughput is not
visible to the runtime. Like the runtime, each publisher reports its own metrics
to a file rather than only to stdout. Point it at a path with:

```shell
export DRAVA_PUBLISHER_METRICS_FILE=/tmp/drava_pub_metrics.json
```

When set, the publisher writes a **single JSON object** at completion:
`{"frames": N, "duration_s": X, "avg_fps": Y[, "eos_seq": S]}`. The benchmark
drivers set this per run and read the file; the human-readable `Done: published
…` line is still printed to the publisher log but is no longer parsed.

#### Energy

When available, the runtime reports **energy** in the same metrics record,
measured from hardware counters over the runtime's own stage window (from the
first frame to end-of-stream) — not sampled and integrated in Python:

- `gpu_energy_j` — GPU energy from NVML's
  `nvmlDeviceGetTotalEnergyConsumption` (a monotonic mJ counter, Volta+). Only
  present when Drava is built with NVML (see below).
- `cpu_energy_j` — CPU package energy from the Linux RAPL powercap sysfs
  (`/sys/class/powercap/intel-rapl:*`). Present on Linux when the domains are
  readable.
- `total_energy_j`, `total_energy_j_per_frame` — sum of the available sources.

Any field whose source is unavailable is simply omitted, so consumers must treat
these as optional. GPU energy requires an NVML-enabled build:

```shell
# NVML ships with the CUDA toolkit/driver. Point Drava at it (or set CUDA_HOME):
export NVML_ROOT=$CUDA_HOME        # or e.g. /usr/local/cuda
# then configure/build as usual; CMake prints whether NVML was enabled.
```

Without NVML, the runtime still reports CPU (RAPL) energy on Linux and omits the
GPU fields. GPU power/utilization/memory *averages* (as opposed to energy)
remain sampled by the benchmark via `nvidia-smi`.

## Paper Experiments

The submitted-paper experiment index is in [experiments.md](experiments.md).
Experiment drivers, preserved logs, result CSVs, and figure-generation packages
are organized under [experiments](experiments). Final submitted figure copies
are in [figs/paper_figs](figs/paper_figs).

## Tests
### Dependency
- [Check unit testing framework](https://libcheck.github.io/check/index.html)
- [Bats-core: Bash automated testing system](https://bats-core.readthedocs.io/en/stable/)

### Setup tests in JLSE
- Install `Check`:
```shell
wget https://github.com/libcheck/check/archive/refs/tags/0.15.2.zip
unzip 0.15.2.zip
cd check-0.15.2
module load cmake
mkdir build-gcc && cd build-gcc
CC=gcc CXX=g++ cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/opt/check-0.15.2
make -j
make install
```
- Install `Bats`:
```shell
git clone https://github.com/bats-core/bats-core.git
cd bats-core
git checkout v1.13.0
./install.sh "$HOME/opt/bats-1.13.0"
```
- Set the environment variables:
```shell
# Add to .zshrc/.bashrc
export CHECK_ROOT="$HOME/opt/check-0.15.2"
export NATS_ROOT="$HOME/opt/nats"
# Add binaries to PATH
export PATH="$HOME/nats_binary:$PATH"
export PATH="$HOME/opt/bats-1.13.0/bin:$PATH"
```
- Run all tests
```shell
ctest --test-dir $HOME/drava/build/tests --output-on-failure
```
- Transport specific tests for Drava C API:
```shell
# Enable JetStream tests (requires a running NATS server)
USE_NATS=1 ctest --test-dir $HOME/drava/build/tests --output-on-failure
USE_NATS=1 ctest --test-dir $HOME/drava/build/tests -R transport_nats -V
# Enable socket tests (requires socket endpoint to exist)
USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests --output-on-failure
USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests -R transport_socket -V
# Enable both (requires both NATS server and socket running)
USE_NATS=1 USE_SOCKET=1 ctest --test-dir $HOME/drava/build/tests --output-on-failure
```
- Integration test with verbose:
```
ctest --test-dir $HOME/drava/build/tests -R integration_transport_jetstream_python -V
ctest --test-dir $HOME/drava/build/tests -R integration_transport_socket_python -V
```
### References
- [NATS C client](https://github.com/nats-io/nats.c/)
- [Check unit testing framework](https://libcheck.github.io/check/index.html)
- [Bats-core: Bash Automated Testing System](https://bats-core.readthedocs.io/en/stable/)
