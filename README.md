# Drava

Drava is a streaming runtime for scientific data pipelines. It moves data frames
from an instrument or data source, through one or more processing or inference
stages, and on to the next stage or an output — at high rate, on HPC hardware.

You write a small Python function for each stage; Drava handles the rest:
receiving data, grouping it into batches, running your function across threads,
signaling the end of a run, and recording performance and energy measurements.

Drava is developed at Argonne National Laboratory and is built on the
[xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) task runtime. It has been used for
ptychographic reconstruction (PtychoNN) and tomographic denoising (TomoGAN).

## Why Drava

Detector and inference pipelines usually re-implement the same plumbing for every
experiment: connecting to a message system, batching frames, spreading work
across threads, and cleaning up at the end of a run. Drava provides that plumbing
once so you can focus on the science:

- **Write only the stage logic.** A stage is a Python function plus one call to
  `drava.run(func)`.
- **Configure, don't code.** Threads, batch sizes, transport, and stage wiring
  live in a `pipeline.yaml` file, not in your program.
- **Choose a transport.** Frames can arrive over NATS JetStream or a Unix socket.
- **Measure everything.** Each stage records throughput, latency, and (where
  available) GPU/CPU energy, written as JSON for analysis.

## How it works

```
 data source ──▶ stage 1 ──▶ stage 2 ──▶ ... ──▶ output
 (publisher)    (your func)  (your func)
```

Each stage is a separate process. A stage reads its settings from `pipeline.yaml`
and runs your callback on each incoming batch of frames. Transform stages publish
their results to the next stage; the final stage writes the output.

A minimal stage:

```python
import drava

def process(frames, base_index):
    for frame in frames:            # frames: list of raw byte payloads
        result = run_model(frame)
        drava.publish_py(result)    # send downstream

drava.run(process)
```

## Metrics

At the end of a run, each stage reports the following (to the console, and to a
JSON file when configured). Pipeline-wide numbers (end-to-end latency, publisher
rate) are assembled from these per-stage records by the benchmark drivers.

| Metric | Meaning |
| --- | --- |
| `stage_total_fps` | Frames processed per second by the stage. |
| `stage_avg_ms` / `stage_max_ms` | Average / maximum per-frame processing latency. |
| `cb_total_s` | Total time spent in your callback. |
| `compute_total_s` | Callback time excluding downstream publishing. |
| `publish_total_s` | Time spent publishing results downstream. |
| `rx_items` / `rx_bytes` | Frames / bytes received. |
| `tx_msgs` / `tx_bytes` | Messages / bytes published downstream. |
| `gpu_energy_j` | GPU energy over the run (NVML; when available). |
| `cpu_energy_j` | CPU package energy over the run (RAPL on Linux). |
| `total_energy_j_per_frame` | Energy per frame from the available sources. |

To capture metrics in a file, set an output path per stage in `pipeline.yaml`:

```yaml
stages:
  - name: stage1
    metrics:
      output_path: /tmp/drava_stage1_metrics.jsonl
```

The runtime appends one JSON record per run. Energy fields are included only when
their hardware source is available.

## Getting started

1. **Build the runtime** — see [docs/build.md](docs/build.md) (generic) or
   [docs/jlse.md](docs/jlse.md) (the Argonne JLSE cluster, with datasets).
2. **Run an example** — see [docs/examples.md](docs/examples.md). For example,
   the two-stage PtychoNN pipeline:

   ```shell
   cd examples/ptychonn
   python benchmark_two_stages.py --batches 256 --runs 1 --num-frames 10000 \
       --threads 4 --rate-hz 1000 --nats-url nats://127.0.0.1:4222
   ```

3. **Write your own app** — see [docs/new-app.md](docs/new-app.md).

## Documentation

| Topic | Guide |
| --- | --- |
| Build the runtime | [docs/build.md](docs/build.md) |
| Build and run on JLSE (with datasets) | [docs/jlse.md](docs/jlse.md) |
| Run the example applications | [docs/examples.md](docs/examples.md) |
| Write, add, or modify an app | [docs/new-app.md](docs/new-app.md) |
| Reproduce the paper results | [docs/paper.md](docs/paper.md) |
| Configuration reference | [docs/configuration.md](docs/configuration.md) |
| `drava-pipeline` helper CLI | [docs/utils.md](docs/utils.md) |

## Example applications

Each example has its own README under [examples/](examples):

| Example | Description |
| --- | --- |
| [PtychoNN](examples/ptychonn) | Two-stage ptychographic inference. |
| [TomoGAN](examples/tomogan) | Tomographic denoising with energy reporting. |
| [Iris KNN](examples/iris_knn) | Minimal single-stage inference. |
| [Bare runtime](examples/bare_runtime) | Runtime message-rate ceiling (no model). |
| [Dataflow](examples/dataflow) | Minimal transport demonstration. |

Shared helpers live in [examples/common](examples/common).

## Tests

The Python tests run anywhere (no runtime build required):

```shell
python examples/common/tests/run_tests.py
```

The C runtime tests (Check + Bats) run against a build directory; see
[docs/jlse.md](docs/jlse.md).

## License

See [LICENSE](LICENSE). Contributors are listed in [AUTHORS](AUTHORS).
