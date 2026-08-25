# Status

Single source of truth for what we're working on right now. Overwrite this file
at the end of each session with the next concrete step. History lives in
[LOGBOOK.md](LOGBOOK.md); plans live in [plans/](plans/).

---

**Active plan:** [plans/2026-07-13-roadmap.md](plans/2026-07-13-roadmap.md) (roadmap index)

**Phase:** Theme A (config docs) done. Theme C + launcher done: `examples/common/`
shared package (config reader + validator + publisher helpers + `drava-pipeline`
CLI) landed and locally verified. Not committed.

**Next concrete step:** On JLSE, exercise end-to-end with the built `drava`
module + NATS: (1) the launcher —
`python -m drava_common.cli run examples/ptychonn/pipeline.yaml
--publisher "python publisher_jetstream.py"`; (2) the rewritten publishers
(all four now route through `drava_common.publish_stream` /
`socket_publish_stream`). Confirm stages come up, data flows, EOS finalizes, and
metrics JSONL + publisher metrics files appear. All four publishers were reduced
to payload-source + transport; verify the tomogan JetStream retry path still
survives a slow consumer.

**Follow-ups surfaced:**
- `examples/iris_knn` and `examples/dataflow` ship **no `pipeline.yaml`** → socket
  defaults only; add a minimal stage config to enable NATS + the launcher.
- Single-stage `benchmark.py` passes the base YAML unmodified, so `--threads` /
  `--batches` do not reach the runtime (documented inline; needs per-run YAML).

**Notes:** C++ build is JLSE-only. The `examples/common` package is pure Python
and verified locally (7/7 config tests, CLI validate/run/new-app). A git-ignored
`.venv/` and `.scratch/` are used for local checks; keep all work inside the repo
(see AGENTS.md §6).
