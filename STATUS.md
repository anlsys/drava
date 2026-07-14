# Status

Single source of truth for what we're working on right now. Overwrite this file
at the end of each session with the next concrete step. History lives in
[LOGBOOK.md](LOGBOOK.md); plans live in [plans/](plans/).

---

**Active plan:** [plans/2026-07-13-roadmap.md](plans/2026-07-13-roadmap.md) (roadmap index)

**Phase:** Planning complete — no theme in execution yet.

**Next concrete step:** Pick a theme to execute. Recommended first strike is
**A + C together** (both fully local-verifiable):
- Theme A — [plans/2026-07-13-theme-a-config-clarity.md](plans/2026-07-13-theme-a-config-clarity.md):
  fix misleading config docs; make `pipeline.yaml` authoritative in the README.
- Theme C — [plans/2026-07-13-theme-c-dedup-examples.md](plans/2026-07-13-theme-c-dedup-examples.md):
  create `examples/common/` shared library; remove ~10 duplicated helpers.

**Blocked on:** user selection of which theme(s) to start.

**Notes:** C++ build is JLSE-only; themes A, B, C and the Python parts of D are
verifiable on a dev machine, themes E and F-NATS require JLSE.
