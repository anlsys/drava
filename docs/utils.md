# Developer utilities

## `drava-pipeline`

`drava-pipeline` is an optional convenience CLI (implemented in
[examples/common](../examples/common)) for working with pipelines during
development. It is **not** required to run apps or reproduce the paper
experiments — those use the manual flow (see
[docs/examples.md](examples.md)) and the example benchmark drivers.

It can:

- **validate** a `pipeline.yaml` (checks stage wiring, EOS forwarding, required
  fields);
- **scaffold** a new app (`pipeline.yaml` + `app.py`, plus `app_stageN.py` for
  extra stages);
- **run** a pipeline: launch every stage with the correct `DRAVA_STAGE_NAME`
  wired automatically (downstream stages first), optionally starting NATS and
  the publisher.

Run the `drava-pipeline` script at the repo root; it self-bootstraps, so no
`pip install` and no `PYTHONPATH` are needed:

```shell
# Validate stage wiring (egress of stage N must match ingress of stage N+1):
./drava-pipeline validate examples/ptychonn/pipeline.yaml

# Scaffold a new app + pipeline.yaml:
./drava-pipeline new-app myapp --stages 2

# Launch all stages plus the publisher, managing NATS automatically:
./drava-pipeline run examples/ptychonn/pipeline.yaml \
    --start-nats \
    --publisher "python publisher_jetstream.py"
```

It can also run as a module without installing (note the `PYTHONPATH`):

```shell
PYTHONPATH=examples/common python -m drava_common.cli validate examples/ptychonn/pipeline.yaml
```

### `run` behavior

- Sets `DRAVA_STAGE_CONFIG` and `DRAVA_STAGE_NAME` per stage — the only two env
  vars the runtime reads for stage identity — so they are never hand-exported.
- Refuses to launch if the config fails validation (e.g. stage1's egress
  stream/subject doesn't match stage2's ingress).
- For the NATS transport, verifies a server is reachable before launching stages
  (they abort on connect failure) and prints a clear message if not.
  `--start-nats` starts `nats-server -js` and stops it on exit; customize with
  `--nats-command` / `--nats-config`.
- If any stage exits abnormally, the whole pipeline is torn down and the
  non-zero exit code is returned.

### Flags

| Flag | Applies to | Purpose |
|---|---|---|
| `--publisher "CMD"` | `run` | Launch a data-source command after stages are up |
| `--start-nats` | `run` | Start/stop a local `nats-server -js` for the NATS transport |
| `--nats-command` | `run` | nats-server executable (default `nats-server`) |
| `--nats-config` | `run` | nats-server config file (else `-js -p PORT`) |
| `--app-cmd STAGE=CMD` | `run` | Override the command used to launch a stage |
| `--workdir DIR` | `run` | Directory to launch stage commands in (default: config's dir) |
| `--dir DIR` | `new-app` | Target directory (default `examples/NAME`) |
| `--stages N` | `new-app` | Number of stages to scaffold |

## Tests

Pure-Python tests for the shared library and this CLI run anywhere (no runtime
build needed):

```shell
python examples/common/tests/run_tests.py
```

See [examples/common/tests/README.md](../examples/common/tests/README.md) for
what each module covers.
