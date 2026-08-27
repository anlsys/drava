# Drava Logbook

Append-only record of dated decisions, cross-referencing the plan file each one
executed. Newest entries at the top. See [STATUS.md](STATUS.md) for the current
active plan and next concrete step.

Entry format:
```
## YYYY-MM-DD — <short title>
Plan: plans/<plan-file>.md
Decision: <what was decided/done and why, in 1-3 sentences>
Result: <what landed / verification outcome>
```

---

## 2026-08-27 — Fix launcher busy-loop on stage death; surface stage1 SIGSEGV
Plan: (launcher UX bugfix)
Decision: On JLSE, stage1 exited rc=-11 (SIGSEGV) and the launcher spammed
"stage 'stage1' exited rc=-11" hundreds of times and hung until ^C. The
`cmd_run` wait-loop re-detected the same dead proc every iteration and its break
conditions never fired. Rewrote the monitor: report each process exit once; if
any *stage* exits abnormally, tear down the whole pipeline and return its code;
otherwise stop when all procs have exited. Verified locally by simulating a
stage crash — exactly one report, immediate teardown of the other stage + NATS,
correct non-zero rc, no spin/hang.
Open (runtime, not launcher): stage1's rc=-11 SIGSEGV at startup is the recurring
C++ runtime crash (seen intermittently before); stage2's later
`FATAL "Fetch error: Limit reached"` (transport_js.cc:322, a LOGGER_FATAL) is a
downstream symptom + a Theme-E abort-on-error case. Needs a JLSE stack trace
(gdb/core) to fix; cannot reproduce off-JLSE. Not committed [superseded by commit].

## 2026-08-27 — Fix launcher stage-app resolution (stage2 ran app.py)
Plan: (launcher UX bugfix)
Decision: JLSE `drava-pipeline run` (invoked from ~/drava) had stage2 crash with
"payload mismatch: got 524469 bytes, expected 16384" — it was running app.py
(stage1's raw-frame code) instead of app_stage2.py, so it parsed stage1's
prediction messages as input frames. Root cause: `_default_app_cmd` checked
`Path("app_stageN.py").exists()` relative to the launcher's CWD, not the stage
workdir (the config's dir), so the file was "not found" and it fell back to
app.py. Fixed to resolve `app_stageN.py` against the workdir.
Result: verified with a 2-stage scaffold run from the repo root — stage2 now
launches app_stage2.py, stage1 app.py (previously both got app.py). 7/7 config +
4/4 publisher tests still pass. Not committed.

## 2026-08-27 — Launcher manages NATS (preflight + --start-nats)
Plan: (continuation of Theme C / launcher UX)
Decision: JLSE run of `drava-pipeline run` failed with a wall of
ConnectionRefused tracebacks + stage FATAL "No server available" because no NATS
server was running — the launcher (unlike benchmark_two_stages.py) didn't start
or check for one. Made `cmd_run` NATS-aware: for `transport.type: nats` it now
(a) preflights reachability and exits with one clear actionable line if no server
is up, and (b) with `--start-nats` starts `nats-server -js` (or `--nats-config`),
waits until reachable, and stops it on exit. Added `--nats-command`/`--nats-config`.
Result: verified locally with a fake nats-server — full start→ready→launch→stop
flow returns rc=0; the no-server path fails fast with the guidance message; 7/7
config + 4/4 publisher tests still pass. (Fixed a missing `import time` in cli.py
found during testing.) The two-stage benchmark remains the behavior baseline
(publisher≈999.8/stage1≈919.5/stage2≈646.1 on the latest JLSE run). Not committed.

## 2026-08-25 — Drop `pip install -e` for the CLI; add repo-root launcher script
Plan: (continuation of Theme C)
Decision: User dislikes `pip install -e examples/common` for the CLI. Replaced it
with a self-bootstrapping `drava-pipeline` script at the repo root (adds
`examples/common` to sys.path, then calls `drava_common.cli.main`), mirroring how
the example publishers already locate `drava_common`. No install, no PYTHONPATH.
Removed `examples/common/pyproject.toml` (its only purpose was the install path)
and updated root + examples/common READMEs to use `./drava-pipeline ...`.
Result: `./drava-pipeline validate|run|new-app` verified locally (also via
explicit interpreter); 7/7 config + 4/4 publisher tests still pass. Publishers
were already install-free via their sys.path shim; nothing else depended on the
package being installed. Not committed.

## 2026-08-25 — JLSE verification of publisher redesign + launcher; two fixes
Plan: (continuation of Theme C)
Decision/Result: First JLSE build+run of this branch. Build succeeded (NATS
enabled, NVML absent so CPU/RAPL-only which is expected; one benign
missing-field-initializer warning in transport_js.cc). Verified on an A100 node:
- `test_config.py` 7/7.
- `two_stage benchmark` matched the pre-change baseline (publisher≈999.7,
  stage1≈913.6, stage2≈649.8 fps vs prior 999.8/918.0/651.9) — the rewritten
  publishers + shared publish loop are behavior-preserving.
Two issues found and fixed:
1. `test_publisher.py::test_publish_stream_retry_on_apierror` FAILED on JLSE
   (passed-as-skip locally because nats-py absent). The fake error wasn't a real
   `nats.js.errors.APIError`, so the retry `except` didn't catch it. Fixed to
   raise a real APIError(err_code=10167); re-verified locally after
   `pip install nats-py` (now runs the real branch, 4/4).
2. `python -m drava_common.cli` failed with ModuleNotFoundError because
   `examples/common` isn't on the path. Fixed the docs (root README +
   examples/common/README) to install with `pip install -e examples/common`
   (provides both the `drava-pipeline` script and the import) or run with
   `PYTHONPATH=examples/common`. Verified editable install → `drava-pipeline`
   and module form both work.
Observation (pre-existing, not from this branch): on the *first* two-stage run
stage2 died with rc=-11 (SIGSEGV) during XKRT/CUDA init (got to "JetStream
trying to connect"); the immediate rerun succeeded. Likely a runtime
startup/init race, worth a separate investigation. Not committed.

## 2026-08-25 — Publisher redesign onto drava_common; single-stage benchmark archived
Plan: (continuation of Theme C)
Decision: Redesigned the example publishers as "payload source + transport",
with all generic plumbing shared. Added `connect_jetstream` (connect + idempotent
add_stream) and folded retry/backoff on JetStream overflow (APIError 10167, from
tomogan) into `drava_common.publish_stream` for every publisher; `publish_stream`
now also drains the client. Rewrote all four example publishers
(ptychonn/tomogan × jetstream/socket) to ~20 lines each — they only pick the
payload source now. Moved the unmaintained single-stage
`examples/ptychonn/benchmark.py` to `examples/ptychonn/archive/rough/benchmark.py`
(paper artifact for the PvaPy comparison); updated experiments.md + the ptychonn
README to point at it and to prefer `benchmark_two_stages.py`.
Result: 11/11 pure-Python tests pass (7 config/validator + 4 publisher:
frames+EOS, metrics file, socket wire format, retry-skips-without-nats). All four
rewritten publishers import cleanly through `drava_common` (verified with local
nats/h5py/imageio stubs). Scratch kept under repo `.scratch/` per AGENTS.md §6.
Not committed.

## 2026-08-25 — Theme C + launcher: examples/common/ shared package
Plan: [plans/2026-07-13-theme-c-dedup-examples.md](plans/2026-07-13-theme-c-dedup-examples.md) (plus new launcher/validator/scaffolder work)
Decision: Built a shared `examples/common/drava_common` package to stop the
copy-paste and make Drava feel more like numaflow: (1) one Python `pipeline.yaml`
reader + a wiring validator (`config.py`), replacing the ~4 hand-rolled parsers;
(2) shared publisher helpers (config/metrics/EOS/pacing) in `publisher.py`;
(3) a `drava-pipeline` CLI (`cli.py`) with `validate` / `run` (launches every
stage with the correct DRAVA_STAGE_NAME, downstream-first, refuses on broken
wiring) / `new-app` scaffolder. Refactored ptychonn+tomogan `publisher_util.py`
to delegate to the package. Cleaned dead benchmark env vars: kept app-side
`DRAVA_INFER_BATCH` (app.py warmup), removed truly-dead `DRAVA_THREADS`,
`DRAVA_CALLBACK_BATCH`, `DRAVA_STAGE1_CALLBACK_BATCH` (+ its unused config.py
assignment). Noted single-stage benchmark.py passes base YAML unmodified so
--threads/--batches don't reach the runtime (documented, not yet fixed).
Result: 7/7 config/validator unit tests pass with and without PyYAML; CLI
validate/run/new-app verified locally (launch order, env wiring, broken-wiring
rejection, scaffold+validate round-trip); refactored publisher_util imports
verified. Pure-Python; no JLSE build needed. Also added a hard filesystem-scope
rule to AGENTS.md (work only inside the repo). Not committed.

## 2026-08-25 — Theme A executed: config docs made honest
Plan: [plans/2026-07-13-theme-a-config-clarity.md](plans/2026-07-13-theme-a-config-clarity.md)
Decision: Confirmed via `src/drava_internal.cc` that the runtime reads only
`DRAVA_STAGE_CONFIG`, `DRAVA_STAGE_NAME`, and `DRAVA_METRICS_FILE`; transport,
threads, streams, batching all come from `pipeline.yaml`. Rewrote the root README
config section (pipeline.yaml authoritative + real-env-var + precedence tables)
and removed dead `DRAVA_TRANSPORT`/`DRAVA_THREADS`/etc. instructions from the
ptychonn, iris_knn, dataflow, and tomogan READMEs and the iris_knn app.py comment.
Noted that iris_knn and dataflow ship **no** `pipeline.yaml`, so they only run on
the socket transport with defaults unless a stage config is created.
Result: README + 4 example READMEs + iris_knn/app.py updated; iris_knn/app.py
re-parsed OK. Grep confirms remaining dead-var mentions are only in meta files
(HANDOFF/AGENTS/plans), the intentional README "older docs" note, and preserved
`experiments/logs/archive/`. Doc-only change; no C++ rebuild needed. Not committed.

## 2026-07-13 — Improvement roadmap authored (planning only)
Plan: [plans/2026-07-13-roadmap.md](plans/2026-07-13-roadmap.md)
Decision: Surveyed the codebase for maintainability/user-friendliness gaps and
split the findings into six independently executable themes (A–F), each in its
own plan file. No code changed in this session — roadmap only.
Result: `plans/` populated with the roadmap index + themes A–F. Active plan set
in STATUS.md. Nothing implemented yet.

## 2026-07-13 — Publisher metrics moved off stdout
Plan: (pre-workshop-structure; not filed as a dated plan)
Decision: The publisher (a non-runtime NATS/socket client) was the last process
whose metrics were scraped from a `Done:` stdout line. Made it write a single
JSON object to `DRAVA_PUBLISHER_METRICS_FILE`; benchmarks read the file.
Result: `PUB_DONE_RE` removed from all 3 benchmark drivers; `Done:` line kept for
humans. Verified via write/read round-trip; C++ build is JLSE-only.

## 2026-07-13 — Runtime energy via NVML + RAPL
Plan: (pre-workshop-structure)
Decision: Energy was estimated in Python (nvidia-smi power sampling + integration
over a guessed window). Moved to exact hardware counters in the runtime:
`nvmlDeviceGetTotalEnergyConsumption` (GPU, optional NVML build) and RAPL sysfs
(CPU), baselined at the true stage window; emitted into the metrics JSONL.
Result: New `src/energy.cc`; tomogan benchmark reads energy from the file and
drops its nvidia-smi/RAPL Python code. GPU telemetry (power/util/mem) stays
sampled. NVML is an optional dependency (mirrors NATS).

## 2026-07-13 — Runtime metrics file sink (JSONL)
Plan: (pre-workshop-structure)
Decision: Benchmarks scraped the `[drava-metrics]` console line via a fragile
regex. Added an opt-in JSONL sink (`DRAVA_METRICS_FILE` / `metrics.output_path`);
benchmarks read the file and filter by `stage`/`reason`.
Result: `drava_stats_log_snapshot` appends one JSON record per snapshot; all 3
benchmark drivers migrated off the regex.

## 2026-07-13 — Runtime-owned EOS lifecycle + drava.run()
Plan: (pre-workshop-structure)
Decision: Example apps hand-rolled EOS bookkeeping (locks, counters,
forward-once) that the runtime already tracked with atomics. Moved EOS
strip/finalize/forward and per-frame base_index into the runtime; added
`drava.run()` and an `on_end_of_stream` hook.
Result: Stateless callbacks (no app-side lock at any thread count); ptychonn
app.py ~188→~55 lines; all examples migrated. `forward_eos` driven by
pipeline.yaml.

---

## Dead Ends

_(none yet — record abandoned approaches here, referencing the plan file that was
abandoned and why)_
