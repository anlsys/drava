# Drava

Drava is an event-driven runtime for scientific streaming pipelines. It moves
data frames from an instrument or data source, through one or more processing or
inference stages, and on to the next stage or an output.

Each stage is a small Python function; Drava handles the rest: receiving data,
grouping it into batches, running the function across threads, signaling the end
of a run, and recording performance and energy measurements.

Drava targets a single GPU node — a near-facility or edge inference node that
uses HPC-class hardware — rather than multi-node distribution. It is developed at
Argonne National Laboratory and built on the
[xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) task runtime. It has been evaluated
on ptychographic reconstruction (PtychoNN) and tomographic denoising (TomoGAN)
on a single NVIDIA A100 node.

## Why Drava

Detector and inference pipelines usually re-implement the same plumbing for every
experiment: connecting to a message system, batching frames, spreading work
across threads, and cleaning up at the end of a run. Drava provides that plumbing
once, leaving applications to focus on the science:

- **Only the stage logic is application code.** A stage is a Python function plus
  one call to `drava.run(func)`.
- **Configure, don't code.** Threads, batch sizes, transport, and stage wiring
  live in a `pipeline.yaml` file, not in application code.
- **Choose a transport.** Frames can arrive over NATS JetStream or a Unix socket.
- **Measure everything.** Each stage records throughput, latency, and (where
  available) GPU/CPU energy, written as JSON for analysis.

## How it works

![Drava workflow](docs/figures/workflow.png)

An application provides the stage logic and a small YAML configuration; Drava
runs the callbacks across workers and GPUs and reports metrics:

1. **Interface** — register a stage callback with `drava.run(func)`.
2. **Configure** — describe stages, transport, threads, and batching in
   `pipeline.yaml`.
3. **Execute** — Drava schedules work across threads and GPUs via the xkrt
   runtime.
4. **Observe** — each stage reports throughput, latency, and energy for analysis
   and tuning.

Each stage is a separate process. A stage reads its settings from `pipeline.yaml`
and runs the callback on each incoming batch of frames. Transform stages publish
their results to the next stage; the final stage writes the output. See
[docs/new-app.md](docs/new-app.md) for the stage callback API.

## Metrics

At the end of a run, each stage reports the following (to the console, and to a
JSON file when configured). Pipeline-wide numbers (end-to-end latency, publisher
rate) are assembled from these per-stage records by the benchmark drivers.

| Metric | Meaning |
| --- | --- |
| `stage_total_fps` | Frames processed per second by the stage |
| `stage_avg_ms` / `stage_max_ms` | Average / maximum per-frame processing latency |
| `cb_total_s` | Total time spent in the callback |
| `compute_total_s` | Callback time excluding downstream publishing |
| `publish_total_s` | Time spent publishing results downstream |
| `rx_items` / `rx_bytes` | Frames / bytes received |
| `tx_msgs` / `tx_bytes` | Messages / bytes published downstream |
| `gpu_energy_j` | GPU energy over the run (NVML; when available) |
| `cpu_energy_j` | CPU package energy over the run (RAPL on Linux) |
| `total_energy_j_per_frame` | Energy per frame from the available sources |

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
2. **Run an example** — see [docs/examples.md](docs/examples.md).
3. **Add a new app** — see [docs/new-app.md](docs/new-app.md).

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
| [PtychoNN](examples/ptychonn) | Two-stage ptychographic inference |
| [TomoGAN](examples/tomogan) | Tomographic denoising with energy reporting |
| [Iris KNN](examples/iris_knn) | Minimal single-stage inference |
| [Bare runtime](examples/bare_runtime) | Runtime message-rate ceiling (no model) |
| [Dataflow](examples/dataflow) | Minimal transport demonstration |

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
