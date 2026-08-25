# drava_common — shared helpers + pipeline launcher

Generic plumbing shared by the Drava example apps, so a new example needs only
an `app.py` (a callback + `drava.run`) and a `pipeline.yaml` — not a copy of the
publisher/benchmark boilerplate.

## What's here

- `drava_common/config.py` — the **single Python reader** for `pipeline.yaml`
  (`load_pipeline_config`, `PipelineConfig`) plus a **wiring validator**
  (`validate_pipeline`). Uses PyYAML when available, falls back to a minimal
  built-in parser otherwise. Mirrors the schema the C++ runtime reads via
  yaml-cpp; it never invents new runtime behavior.
- `drava_common/publisher.py` — shared publisher helpers: config resolution
  (`load_transport_config`, `load_publish_config`), the JetStream/socket publish
  loops (`publish_stream`, `socket_publish_stream`) with pacing + EOS emission,
  and `write_publisher_metrics`.
- `drava_common/cli.py` — the `drava-pipeline` command.

## Install

```shell
pip install -e examples/common      # provides the `drava-pipeline` script
```

This puts both the `drava-pipeline` command and the `drava_common` package on
the path. (The example `publisher_*.py` files also add `examples/common` to
`sys.path` themselves, so the *publishers* import `drava_common` without an
install; the CLI, however, needs either the install above or
`PYTHONPATH=examples/common`.)

## The `drava-pipeline` CLI

```shell
# Validate a pipeline (checks stage wiring, EOS forwarding, required fields):
drava-pipeline validate examples/ptychonn/pipeline.yaml

# Launch every stage with the correct DRAVA_STAGE_NAME wired automatically
# (downstream stages start first). Run the publisher separately, or pass one:
drava-pipeline run examples/ptychonn/pipeline.yaml
drava-pipeline run examples/ptychonn/pipeline.yaml --publisher "python publisher_jetstream.py"

# Scaffold a new example (single- or multi-stage):
drava-pipeline new-app myapp --stages 2
```

Without installing, run it as a module (note the `PYTHONPATH`):

```shell
PYTHONPATH=examples/common python -m drava_common.cli validate examples/ptychonn/pipeline.yaml
```

`run` sets `DRAVA_STAGE_CONFIG` and `DRAVA_STAGE_NAME` per stage — the only two
env vars the runtime reads for stage identity — so you never hand-export them.
It refuses to launch if the config fails validation (e.g. stage1's egress
stream/subject doesn't match stage2's ingress).

## Tests

```shell
python examples/common/tests/test_config.py      # no pytest needed
# or: python -m pytest examples/common/tests -q
```

These are pure-Python and run on any machine (they do not need the JLSE
runtime).
