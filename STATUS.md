# Status

Single source of truth for what we're working on right now. Overwrite this file
at the end of each session with the next concrete step. History lives in
[LOGBOOK.md](LOGBOOK.md); plans live in [plans/](plans/).

---

**Active plan:** [plans/2026-07-13-roadmap.md](plans/2026-07-13-roadmap.md) (roadmap index)

**Phase:** Theme A (config docs) done. Theme C + launcher done: `examples/common/`
shared package (config reader + validator + publisher helpers + `drava-pipeline`
CLI) landed and locally verified. Not committed.

**JLSE status (2026-08-25):** Build OK (NATS on, NVML off → CPU/RAPL energy
only). `test_config.py` 7/7. Two-stage ptychonn benchmark matched the pre-change
baseline, so the publisher rewrite is behavior-preserving. Fixed the retry test
(now uses a real nats APIError) and the CLI docs (`pip install -e examples/common`
or `PYTHONPATH=examples/common`).

**Next concrete step:** Re-run on JLSE (no install — repo-root `./drava-pipeline`,
build dir on PYTHONPATH):
`./drava-pipeline run examples/ptychonn/pipeline.yaml --start-nats
--publisher "python publisher_jetstream.py"`. Two launcher bugs are now fixed:
(1) it starts/preflights NATS (`--start-nats`); (2) stage2 now runs
`app_stage2.py` (previously ran app.py from the repo-root CWD → "payload
mismatch: got 524469 bytes, expected 16384"). Confirm stage2 runs app_stage2.py,
data flows end-to-end, stage2 finalizes, and metrics files appear. The two-stage
benchmark remains the behavior baseline.

**Open issue to investigate:** first two-stage run had stage2 rc=-11 (SIGSEGV)
during XKRT/CUDA init; rerun succeeded. Looks like a runtime startup race,
independent of the Python changes — needs a separate look in src/ (drava.cc init
/ transport_js connect).

**Follow-ups surfaced:**
- `examples/iris_knn` and `examples/dataflow` ship **no `pipeline.yaml`** → socket
  defaults only; add a minimal stage config to enable NATS + the launcher.
- Single-stage `benchmark.py` passes the base YAML unmodified, so `--threads` /
  `--batches` do not reach the runtime (documented inline; needs per-run YAML).

**Notes:** C++ build is JLSE-only. The `examples/common` package is pure Python
and verified locally (7/7 config tests, CLI validate/run/new-app). A git-ignored
`.venv/` and `.scratch/` are used for local checks; keep all work inside the repo
(see AGENTS.md §6).
