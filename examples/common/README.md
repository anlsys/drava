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

The optional `drava-pipeline` launcher/validator/scaffolder is documented in
[docs/utils.md](../../docs/utils.md). Run it from the repo root
(`./drava-pipeline validate|run|new-app ...`); no install or `PYTHONPATH` needed.

## Tests

```shell
python examples/common/tests/run_tests.py        # all modules, no pytest needed
# or a single module: python examples/common/tests/test_cli.py
# or under pytest:     python -m pytest examples/common/tests -q
```

Pure-Python; runs on any machine (no JLSE runtime needed). See
[tests/README.md](tests/README.md) for what each module covers.
