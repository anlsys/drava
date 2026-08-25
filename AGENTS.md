# AGENTS.md — Drava

Instructions for AI coding agents working in this repo. Read this first.

Drava is a C++20 streaming runtime (built on the xkrt task runtime) for
detector/inference dataflow pipelines, with a SWIG Python binding and example
apps (ptychonn, tomogan, iris_knn, bare_runtime, dataflow). Frames enter over a
transport (Unix socket or NATS JetStream), are dispatched in batches to a
user callback, and predictions are published downstream.

---

## 1. Hard constraint: the C++ build is JLSE-only

The runtime depends on **xkrt** (INRIA GitLab), **yaml-cpp**, optionally **NATS
(nats.c)** and **NVML/CUDA**, and a **no-GIL Python 3.14** build — available only
on the JLSE cluster. **Do not attempt to build the C++ runtime or the SWIG
`drava` module on a normal machine; it will fail.**

Verify changes accordingly:
- **Locally (any machine):** `python -m py_compile` changed Python; extract and
  unit-test pure Python functions; `grep` audits; JSON round-trip tests. Do NOT
  claim runtime behavior is verified from a local machine.
- **JLSE only:** CMake build, `ctest`, running any `examples/*/app.py`, energy
  counters, transport connect paths. State clearly when something needs JLSE.

Never report a C++/runtime change as "verified" or "working" without a JLSE
build+run. Say "static-checked; needs JLSE build to verify."

---

## 2. Workshop workflow (planning & session bookkeeping)

Three tracking files live at repo root; keep them current.

- **[STATUS.md](STATUS.md)** — single source of truth for the *active plan* and
  the *next concrete step*. Overwrite it at the end of each session.
- **[LOGBOOK.md](LOGBOOK.md)** — append-only dated decisions (newest first), each
  citing the plan file it executed. Has a **Dead Ends** section.
- **[plans/](plans/)** — one file per plan, named `YYYY-MM-DD-<slug>.md`.

Rules:
- **End of a planning session:** save the plan to `plans/YYYY-MM-DD-<slug>.md`
  and point STATUS.md at it. Do not implement yet.
- **End of an execution session:** append a dated entry to LOGBOOK.md citing the
  plan, then overwrite STATUS.md with the next concrete step in that plan.
- **Revising a plan mid-flight:** save as `...-v2.md`, update STATUS.md, leave v1
  as history.
- **Abandoning a plan:** add an `Abandoned: YYYY-MM-DD, reason: …` header to the
  plan file and append a Dead Ends entry in LOGBOOK.md referencing it.

The current backlog is six themes (A–F) indexed at
[plans/2026-07-13-roadmap.md](plans/2026-07-13-roadmap.md). See
[HANDOFF.md](HANDOFF.md) for full session context.

---

## 3. Runtime conventions (do not regress these)

- **EOS is runtime-owned.** The runtime strips the `DRAVA_EOS:` marker before the
  app callback, tracks completion with atomics, and forwards/finalizes exactly
  once. App callbacks MUST NOT parse `DRAVA_EOS:` themselves — use the
  `on_end_of_stream` hook. Publishers still emit the marker (they are the source).
- **Callbacks are stateless.** `drava.run(func[, on_end_of_stream])` handles
  init/register/listen/deinit. `func` may be `func(frames)` or
  `func(frames, base_index)`; `base_index` is the runtime-assigned global index
  of the first frame in the batch. No app-side lock needed at any thread count.
- **Metrics go to files, not stdout.** The runtime appends one JSON object per
  snapshot to `DRAVA_METRICS_FILE` / `metrics.output_path`. Publishers write a
  single JSON object to `DRAVA_PUBLISHER_METRICS_FILE`. Consumers filter by
  `stage`/`reason` and **ignore unknown keys** (forward-compat). Do NOT
  reintroduce console/log scraping for metrics. Human-readable log lines
  (`[drava-metrics]`, `Done:`) are kept but must not be load-bearing.
- **Energy is optional.** GPU energy needs an NVML build (`DRAVA_HAS_NVML`, set
  `NVML_ROOT`/`CUDA_HOME`). Without it, CPU (RAPL) energy still works on Linux
  and GPU fields are simply omitted. Never hard-require NVML.
- **`pipeline.yaml` is authoritative for the runtime.** Optional deps
  (NATS/NVML) follow the CMake auto-detect pattern (`*_ROOT` → `DRAVA_HAS_*`).

Known wart (Theme A, not yet fixed): the README documents env vars
(`DRAVA_TRANSPORT`, `DRAVA_THREADS`) that the runtime does **not** read; config
precedence is inconsistent (runtime→YAML wins, publishers→env wins). Don't trust
the README config section until Theme A lands.

---

## 4. Code layout

- `src/*.cc` — runtime: `drava.cc` (lifecycle), `drava_internal.cc` (config,
  dispatch, EOS, metrics), `transport_socket.cc`, `transport_js.cc` (NATS),
  `energy.cc` (NVML+RAPL).
- `include/drava/drava.h`, `api/c/include/drava/drava_c.h` — C++/C API.
- `api/python/drava.i` (+ `drava_routine_wrap.c`) — SWIG binding; `drava.run` and
  helpers are here.
- `examples/<name>/` — `app.py` (stage callback), `publisher_*.py` (data source),
  `benchmark*.py` (orchestrator), `pipeline.yaml`, `config.py`.
- `tests/` — Check-based C tests + Bats integration; `experiments/` — paper runs.

Heavy Python duplication exists across `examples/*/benchmark*.py` and
`publisher_util.py` (Theme C) — prefer a shared module over copy-paste.

---

## 5. House rules

- Match surrounding style; a `.clang-format` exists at root (not yet CI-enforced).
- Keep changes minimal and focused; do not commit or push unless the user asks.
  If asked, branch first (current work branch: `feature/simplification`).
- When adding a metric/config field, follow the existing optional-and-ignored
  convention so old readers keep working.

## 6. Filesystem scope (hard rule)

- Work **only inside the project directory** (this repo). Do not read, write, or
  create files anywhere else — no `$HOME`, no system temp dirs like
  `/var/folders/...`, no sibling projects. `/tmp` is a last resort only, and
  only when something truly cannot live in the tree; clean it up immediately.
- Keep all scratch/test artifacts inside the repo: put throwaway virtualenvs,
  generated output, and fixtures under a git-ignored dir in the tree (e.g.
  `.venv/`, `build*/`, `.scratch/`), never outside it.
- Do not run interpreters, tools, or commands that read/write paths outside the
  repo. If a task seems to require it, ask first.
