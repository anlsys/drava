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

## No install needed

Nothing here requires `pip install`:

- The example `publisher_*.py` files add `examples/common` to `sys.path`
  themselves, so they import `drava_common` directly.
- The CLI is run via the `drava-pipeline` script at the repo root, which
  self-bootstraps `sys.path`.

The only hard dependency is **PyYAML** (already in the example requirements);
without it, `config.py` falls back to a minimal built-in parser.

## The `drava-pipeline` CLI

Run the `drava-pipeline` script at the repo root (no install, no `PYTHONPATH`):

```shell
# Validate a pipeline (checks stage wiring, EOS forwarding, required fields):
./drava-pipeline validate examples/ptychonn/pipeline.yaml

# Launch every stage with the correct DRAVA_STAGE_NAME wired automatically
# (downstream stages start first). --start-nats runs/stops a local server for
# the NATS transport; add --publisher to also start the data source:
./drava-pipeline run examples/ptychonn/pipeline.yaml --start-nats \
    --publisher "python publisher_jetstream.py"

# Scaffold a new example (single- or multi-stage):
./drava-pipeline new-app myapp --stages 2
```

`run` sets `DRAVA_STAGE_CONFIG` and `DRAVA_STAGE_NAME` per stage — the only two
env vars the runtime reads for stage identity — so you never hand-export them.
Behavior:
- refuses to launch if the config fails validation (e.g. stage1's egress
  stream/subject doesn't match stage2's ingress);
- for the NATS transport, verifies a server is reachable first (stages abort on
  connect failure) and prints a clear message if not. `--start-nats` starts
  `nats-server -js` and stops it on exit; `--nats-command` / `--nats-config`
  customize that.

## Tests

```shell
python examples/common/tests/test_config.py      # no pytest needed
# or: python -m pytest examples/common/tests -q
```

These are pure-Python and run on any machine (they do not need the JLSE
runtime).
