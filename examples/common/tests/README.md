# drava_common tests

Pure-Python unit tests for the shared example library and the `drava-pipeline`
CLI. They do **not** require the built `drava` runtime, NATS, or JLSE — they run
on any machine with Python (PyYAML optional; a fallback parser is used without
it). This makes them the fast first check before a JLSE build/run.

## Run

```shell
# All modules at once (no pytest needed):
python examples/common/tests/run_tests.py

# Or a single module standalone:
python examples/common/tests/test_config.py
python examples/common/tests/test_publisher.py
python examples/common/tests/test_cli.py

# Or under pytest, if installed:
python -m pytest examples/common/tests -q
```

## What each module covers

| Module | Covers |
|---|---|
| `test_config.py` | `pipeline.yaml` reader + wiring validator: field parsing, broken-wiring rejection, duplicate/missing stages, terminal `forward_eos` warning, missing file. |
| `test_publisher.py` | Shared publish loop: frame count + EOS marker, metrics-file output, retry on a real NATS `APIError` (skipped if `nats-py` absent), socket wire format `[len][bytes]`. |
| `test_cli.py` | Launcher logic: per-stage command resolution (stage2 → `app_stage2.py`, resolved against the stage workdir), `new-app` scaffolder (single/multi-stage, refuses non-empty dir), `validate` accept/reject. |
| `test_examples_import.py` | Smoke-imports the example publishers with heavy deps stubbed; asserts each example's `load_publish_config` return arity matches how the publishers unpack it (guards against integration drift like the TomoGAN 2-tuple bug). |
| `test_reconstruction_accuracy.py` | Confirms reconstruction correctness under the refactored multi-threaded runtime: PtychoNN wire round-trip, and PtychoNN/TomoGAN output is identical whether batches arrive in order, shuffled, or concurrently from 8 threads (order independence via runtime-assigned `base_index`). Needs numpy. |

## Notes

- Scratch files are written under the repo's git-ignored `.scratch/` directory,
  never system temp (see the repo `AGENTS.md` filesystem rule).
- The retry test needs `nats-py` to exercise the real `APIError` branch; without
  it, that single test prints a skip line and still passes.
- These tests exercise everything except behavior that requires the C++ runtime
  (`drava.run`, transport connect, energy counters) — verify those on JLSE.
