# Drava

Drava is an event-driven runtime for edge scientific streaming pipelines. At
facilities like the [Advanced Photon Source][aps], detectors produce data faster
than it can be shipped to a central site, so reconstruction and inference run near
the instrument under latency and throughput constraints. Drava runs these
multi-stage pipelines and manages the system concerns that are usually left to
manual tuning, such as batching, scheduling, and resource placement.

A developer writes each stage as a reusable callback. The runtime manages
microbatching, dispatch, data movement, and observability, which separates the
scientific logic from the system concerns. Drava is built on the [XKRT][xkrt]
tasking runtime.

![Drava workflow](docs/figures/workflow.png)

## Programming model

A Drava workflow is a directed acyclic graph. Nodes are stages and edges are
transport routes. Each stage has an ingress route, a callback that performs the
computation, an egress route for publishing results, and runtime parameters that
control batching, scheduling, and threads.

The application defines the ingress, callback, and egress. The runtime parameters
come from a YAML file, so the same callback runs under different execution
policies without code changes. Stages are stateless functions triggered by data
events.

## Architecture

![Drava layered architecture](docs/figures/architecture.png)

- **Application interface.** Callbacks are registered through a C or Python API.
- **Pipeline configuration.** A YAML file binds each stage to its transport,
  batching policy, and thread team.
- **Execution engine.** Built on XKRT. One I/O thread pulls events, compute
  threads run callback tasks with work-stealing, and a microbatching layer flushes
  on a size threshold, an end-of-stream event, or a timeout. Lock-free atomic
  counters record metrics.
- **Transport.** Stages exchange events over a publish/subscribe model. A stage
  subscribes to its ingress subject and publishes to its egress subject. Drava
  uses two interchangeable backends, a Unix socket for intra-node communication
  and [NATS JetStream][nats] for durable pub/sub across nodes.

## Observability

Each stage records throughput, end-to-end latency, and GPU and CPU energy, and
exposes them as per-run CSV and JSON. This observability drives an agentic
[ytopt][ytopt] search that tunes runtime parameters automatically. The metrics
schema is documented on Read the Docs.

## Documentation

Guides and the generated C and Python API reference are on Read the Docs:
<https://drava.readthedocs.io>.

## Example applications

| Example | Description |
| --- | --- |
| [PtychoNN](examples/ptychonn) | Two-stage ptychographic inference and stitching |
| [TomoGAN](examples/tomogan) | Single-stage tomographic denoising with energy reporting |
| [Iris KNN](examples/iris_knn) | Minimal single-stage inference |
| [Bare runtime](examples/bare_runtime) | Runtime message-rate ceiling, no model |
| [Dataflow](examples/dataflow) | Minimal transport demonstration |

## References

- [XKRT][xkrt], the tasking runtime Drava is built on
- [NATS JetStream][nats], the publish/subscribe transport
- [ytopt][ytopt], the Bayesian optimization framework used for tuning
- [Advanced Photon Source (APS)][aps], Argonne National Laboratory
- [JLSE][jlse], the evaluation cluster at Argonne National Laboratory

## License and authors

Distributed under the terms in [LICENSE](LICENSE). Contributors are listed in
[AUTHORS](AUTHORS).

[xkrt]: https://gitlab.inria.fr/xkaapi/dev-v2
[nats]: https://docs.nats.io/nats-concepts/jetstream
[ytopt]: https://github.com/ytopt-team/ytopt
[aps]: https://www.aps.anl.gov/
[jlse]: https://www.jlse.anl.gov/
