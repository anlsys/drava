# Drava

**An event-driven runtime for scientific streaming pipelines.**

Drava connects a data source to one or more processing or inference stages and
runs them at high frame rates on GPU hardware. A stage is a single Python
callback; the runtime owns the streaming machinery — transport, batching,
multi-threaded dispatch, end-of-stream handling, and per-stage observability —
so applications contain only the science logic.

Developed at Argonne National Laboratory and built on the
[xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) tasking runtime. Evaluated on
ptychographic reconstruction (PtychoNN) and tomographic denoising (TomoGAN).

---

## Highlights

- **Callback programming model** — a stage is a Python function plus one call to
  `drava.run(func)`; the runtime handles the rest.
- **Declarative pipelines** — stages, wiring, thread counts, and batch sizes are
  described in `pipeline.yaml`, not hard-coded.
- **Pluggable transports** — NATS JetStream or Unix-domain socket, selected in
  configuration.
- **Deterministic under concurrency** — the runtime assigns each batch a global
  index, so callbacks run lock-free across threads and produce order-independent
  results.
- **Built-in observability** — per-stage throughput, latency, and GPU/CPU energy
  are emitted as JSON for benchmarking and tuning.

## Architecture

![Drava workflow](docs/figures/workflow.png)

A pipeline is a chain of stages, each a separate process:

```
data source ──▶ stage 1 ──▶ stage 2 ──▶ … ──▶ output
(publisher)     (callback)   (callback)
```

A stage reads its configuration from `pipeline.yaml`, receives frames over the
configured transport, and invokes the application callback on each batch. The
runtime provides four things around that callback:

1. **Interface** — the callback is registered with `drava.run(func)`.
2. **Configuration** — transport, threads, and batching come from `pipeline.yaml`.
3. **Execution** — the xkrt runtime schedules callbacks across worker threads and
   GPUs; each batch carries a runtime-assigned global index.
4. **Observability** — each stage records throughput, latency, and energy.

## Concepts

| Term | Meaning |
| --- | --- |
| Stage | One processing step: an application callback run as a process |
| Callback | `func(frames, base_index)` invoked per incoming batch of frames |
| Transport | How frames move between stages (NATS JetStream or Unix socket) |
| Publisher | The data source that feeds stage 1 |
| Pipeline | A chain of stages wired egress → ingress in `pipeline.yaml` |

End-of-stream is runtime-owned: the runtime strips the marker, drives
finalization once the stream drains, and forwards it downstream. Application
callbacks handle data only. See [docs/new-app.md](docs/new-app.md) for the API.

## Metrics

Each stage reports the following at end-of-run, to the console and to a JSON file
when configured. Pipeline-level figures (end-to-end latency, publisher rate) are
derived from these per-stage records.

| Metric | Meaning |
| --- | --- |
| `stage_total_fps` | Frames processed per second by the stage |
| `stage_avg_ms`, `stage_max_ms` | Mean and maximum per-frame latency |
| `cb_total_s` | Total time in the application callback |
| `compute_total_s` | Callback time excluding downstream publishing |
| `publish_total_s` | Time spent publishing results downstream |
| `rx_items`, `rx_bytes` | Frames and bytes received |
| `tx_msgs`, `tx_bytes` | Messages and bytes published downstream |
| `gpu_energy_j` | GPU energy over the run (NVML, when available) |
| `cpu_energy_j` | CPU package energy over the run (RAPL on Linux) |
| `total_energy_j_per_frame` | Energy per frame from the available sources |

Enable the file sink per stage in `pipeline.yaml`:

```yaml
stages:
  - name: stage1
    metrics:
      output_path: /tmp/drava_stage1_metrics.jsonl
```

Energy fields are included only when their hardware source is available. See
[docs/configuration.md](docs/configuration.md) for the full record schema.

## Getting started

| Step | Guide |
| --- | --- |
| Build the runtime | [docs/build.md](docs/build.md) |
| Build and run on the JLSE cluster (with datasets) | [docs/jlse.md](docs/jlse.md) |
| Run the example applications | [docs/examples.md](docs/examples.md) |
| Write, add, or modify a stage | [docs/new-app.md](docs/new-app.md) |
| Configuration reference | [docs/configuration.md](docs/configuration.md) |
| Reproduce the paper results | [docs/paper.md](docs/paper.md) |
| `drava-pipeline` helper CLI | [docs/utils.md](docs/utils.md) |

## Example applications

| Example | Description |
| --- | --- |
| [PtychoNN](examples/ptychonn) | Two-stage ptychographic inference |
| [TomoGAN](examples/tomogan) | Tomographic denoising with energy reporting |
| [Iris KNN](examples/iris_knn) | Minimal single-stage inference |
| [Bare runtime](examples/bare_runtime) | Runtime message-rate ceiling (no model) |
| [Dataflow](examples/dataflow) | Minimal transport demonstration |

Shared helpers live in [examples/common](examples/common).

## Testing

Pure-Python tests (config parsing, publisher loop, CLI, and reconstruction
correctness under multi-threaded dispatch) run on any machine:

```shell
python examples/common/tests/run_tests.py
```

The C runtime tests (Check + Bats) run against a build directory; see
[docs/jlse.md](docs/jlse.md).

## Project status

Drava is research software. The C++ runtime is developed and tested on the
Argonne JLSE cluster and its native dependencies (xkrt, a no-GIL Python build,
and optionally NATS and NVML) are expected there; the example applications and
tooling are pure Python and run anywhere.

## License and authors

Distributed under the terms in [LICENSE](LICENSE). Contributors are listed in
[AUTHORS](AUTHORS).
