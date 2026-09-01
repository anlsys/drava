# Python API

The `drava_common` package (under `examples/common/`) provides the shared
helpers used by example applications and publishers: pipeline configuration
parsing and validation, the transport publish loops, and metrics helpers. See
[Writing and adding a Drava app](../new-app.md) for how these fit together.

The stage runtime itself is exposed through the compiled `drava` module
(`drava.run`, `drava.publish_py`); because that module is a native extension it
is not imported here — see [Writing and adding a Drava app](../new-app.md).

```{toctree}
:maxdepth: 2

python/drava_common/index
```
