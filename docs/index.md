# Drava

**An event-driven runtime for scientific streaming pipelines.**

Drava connects a data source to one or more processing or inference stages and
runs them at high frame rates on GPU hardware. A stage is a single Python
callback; the runtime owns the streaming machinery — transport, batching,
multi-threaded dispatch, end-of-stream handling, and per-stage observability.

Developed at Argonne National Laboratory and built on the
[xkrt](https://gitlab.inria.fr/xkaapi/dev-v2) tasking runtime.

```{toctree}
:caption: Guides
:maxdepth: 1

build
jlse
examples
new-app
configuration
paper
utils
artifact-description
```

```{toctree}
:caption: API reference
:maxdepth: 2

api/c
api/python-index
```
