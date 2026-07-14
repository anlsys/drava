# Theme A — Config clarity (misleading/dead config)

Date: 2026-07-13
Status: Proposed
Impact: High · Effort: S · Local: Yes
Index: [2026-07-13-roadmap.md](2026-07-13-roadmap.md)

## Context

The README (lines 74–108) and every example README tell users to
`export DRAVA_TRANSPORT=nats|socket`, `DRAVA_THREADS=…`, etc., but the runtime
**never reads these**. Grep confirms no `getenv("DRAVA_TRANSPORT")` /
`DRAVA_THREADS` anywhere in `src/` or `api/`. Transport comes only from
`transport.type` in the YAML ([src/drava_internal.cc:129-138](../src/drava_internal.cc#L129));
threads only from `runtime.threads`. A user following the README is silently
ignored.

Precedence is also inconsistent: runtime → YAML wins; publishers/app config →
env wins (`os.getenv(NAME, yaml_default)`); only `DRAVA_METRICS_FILE` is a
deliberate documented override ([src/drava_internal.cc:250](../src/drava_internal.cc#L250)).

## Fix

- Rewrite the README config section: `pipeline.yaml` is authoritative for the
  runtime; list only env vars actually honored (`DRAVA_STAGE_CONFIG`,
  `DRAVA_STAGE_NAME`, `DRAVA_METRICS_FILE`, plus publisher/app-side vars).
- Delete the dead `export DRAVA_TRANSPORT=…` / `DRAVA_THREADS=…` instructions
  (recommended — YAML is already the design), OR wire them as real overrides in
  `drava_apply_stage_config` ([src/drava_internal.cc:216](../src/drava_internal.cc#L216))
  with documented precedence. **Recommend delete from docs.**
- State precedence explicitly in one table.

## Files to modify

- [../README.md](../README.md) (config section)
- Example READMEs referencing `DRAVA_TRANSPORT` (ptychonn, iris_knn, dataflow, etc.)
- Optionally [../src/drava_internal.cc](../src/drava_internal.cc) if wiring env overrides.

## Verification

- Doc review.
- `grep -rn "getenv" src api` proving no runtime read for the removed vars.
