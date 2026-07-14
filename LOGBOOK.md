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
