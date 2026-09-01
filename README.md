# Drava

Drava is an event-driven runtime for scientific streaming pipelines. It runs
detector and inference workflows that move data frames from a source, through one
or more processing stages, to an output. An application registers each stage as a
callback. The runtime owns microbatching, dispatch, transport, thread placement,
and per-stage observability, so application code stays small.

Drava is developed at Argonne National Laboratory and built on the
[xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) tasking runtime. It was evaluated on
PtychoNN ptychography and TomoGAN tomography on a JLSE GPU node (dual-socket AMD
EPYC 7532 with one NVIDIA A100).

![Drava workflow](docs/figures/workflow.png)

## Architecture

Drava is a layered runtime. An application registers per-stage callbacks through a
C or Python API. A YAML configuration binds each stage to its transport, batching
policy, and thread team without changing application code. An execution engine
performs I/O, microbatching, work-stealing task dispatch, and metrics collection.

Stages exchange events, each carrying an identifier, a timestamp, and a payload,
over two interchangeable transports. Unix sockets are used for intra-node
communication. NATS JetStream (publish/subscribe) is used for streaming across
nodes. Each stage runs as a process with its own thread team, and stages chain
into multi-stage pipelines. For example, PtychoNN stage 1 runs GPU inference and
feeds stage 2, which runs CPU stitching.

## Concepts

| Term | Meaning |
| --- | --- |
| Stage | One processing step, an application callback run as a process |
| Callback | `func(frames, base_index)`, invoked per incoming batch of frames |
| Transport | How frames move between stages, over a Unix socket or NATS JetStream |
| Publisher | The data source that feeds stage 1 |
| Pipeline | A chain of stages wired egress to ingress in `pipeline.yaml` |

## Measurement

Each stage records throughput, end-to-end latency, and GPU and CPU energy, and
writes them as per-run CSV and JSON for benchmarking and tuning. The metrics
schema is documented on Read the Docs.

## Documentation

Guides and the generated C and Python API reference are on Read the Docs:
<https://drava.readthedocs.io>.

## Example applications

| Example | Description |
| --- | --- |
| [PtychoNN](examples/ptychonn) | Two-stage ptychographic inference |
| [TomoGAN](examples/tomogan) | Tomographic denoising with energy reporting |
| [Iris KNN](examples/iris_knn) | Minimal single-stage inference |
| [Bare runtime](examples/bare_runtime) | Runtime message-rate ceiling, no model |
| [Dataflow](examples/dataflow) | Minimal transport demonstration |

## License and authors

Distributed under the terms in [LICENSE](LICENSE). Contributors are listed in
[AUTHORS](AUTHORS).
