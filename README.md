# Drava

**An event-driven runtime for scientific streaming pipelines.**

Drava runs detector and inference pipelines that move data frames from an
instrument or data source, through one or more processing stages, to an output.
An application writes a stage as a single Python callback; the runtime owns the
streaming machinery — microbatching, dispatch, transport, thread placement,
end-of-stream handling, and per-stage observability.

Developed at Argonne National Laboratory and built on the
[xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) tasking runtime. Evaluated on
ptychographic reconstruction (PtychoNN) and tomographic denoising (TomoGAN).

---

## Highlights

- **Callback programming model** — a stage is a Python function plus one call to
  `drava.run(func)`; the runtime handles the rest.
- **Declarative pipelines** — stages, wiring, thread counts, and batch sizes come
  from `pipeline.yaml`, not application code.
- **Deterministic under concurrency** — the runtime assigns each batch a global
  index, so callbacks run lock-free across threads with order-independent results.
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
transport, and invokes the application callback on each microbatch. The runtime
schedules callbacks across worker threads and GPUs via xkrt, tags each batch with
a global index, owns end-of-stream, and records metrics.

## Concepts

| Term | Meaning |
| --- | --- |
| Stage | One processing step: an application callback run as a process |
| Callback | `func(frames, base_index)` invoked per incoming batch of frames |
| Transport | How frames move between stages (NATS JetStream or Unix socket) |
| Publisher | The data source that feeds stage 1 |
| Pipeline | A chain of stages wired egress → ingress in `pipeline.yaml` |

## Metrics

Each stage reports the following at end-of-run, to the console and (when
configured) to a JSON file. Pipeline-level figures such as end-to-end latency are
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

## Documentation

Full guides and the auto-generated C and Python API reference are on
Read the Docs: **<https://drava.readthedocs.io>**.

## Example applications

| Example | Description |
| --- | --- |
| [PtychoNN](examples/ptychonn) | Two-stage ptychographic inference |
| [TomoGAN](examples/tomogan) | Tomographic denoising with energy reporting |
| [Iris KNN](examples/iris_knn) | Minimal single-stage inference |
| [Bare runtime](examples/bare_runtime) | Runtime message-rate ceiling (no model) |
| [Dataflow](examples/dataflow) | Minimal transport demonstration |

## License and authors

Distributed under the terms in [LICENSE](LICENSE). Contributors are listed in
[AUTHORS](AUTHORS).
