# Theme D — Tests + CI (foundational)

Date: 2026-07-13
Status: Proposed
Impact: High · Effort: M–L · Local: Partial
Index: [2026-07-13-roadmap.md](2026-07-13-roadmap.md)

## Context

1,756 lines of runtime `.cc`; the 4 C transport tests **skip by default**
(gated on `USE_SOCKET`/`USE_NATS`) and only assert init/register/deinit return
codes. `transport_socket.c` and `transport_nats.c` are near-duplicates; the two
tests within each file are exact duplicates; `transport_unknown.c`'s
`test_init_invalid_transport_fails` asserts `== DRAVA_SUCCESS` (name contradicts
assertion).

Pure, trivially-testable logic has **zero** tests:
`drava_payload_parse_eos_count` / `drava_payload_is_eos`
([src/drava_internal.cc:263-293](../src/drava_internal.cc#L263)), energy RAPL
wraparound ([src/energy.cc](../src/energy.cc)), metrics JSONL emission
(hand-written `fprintf`, depended on by benchmarks). No CI, no enforced
`.clang-format`, no hooks.

## Fix

- Add focused C unit tests (Check) for the pure functions: EOS parse (digits,
  prefix, `data_len<10` boundary), RAPL wraparound math, and a test that parses
  the emitted metrics JSON and validates fields.
- Fix the misleading test name and de-duplicate the copy-paste transport tests.
- Add Python unit tests (pytest) for binding-level helpers (`drava.run` arity
  adapter, publisher metrics round-trip) — run without the C build.
- Add `.github/workflows/ci.yml`: socket-only build + `ctest` +
  `clang-format --dry-run -Werror` + python tests. Even build+lint+py catches
  most regressions.

## Files to modify

- `tests/` (new unit tests; fix/dedup existing `transport_*.c`).
- New: `tests/python/` (pytest) or `examples/**/tests`.
- New: `.github/workflows/ci.yml`.
- Wire `.clang-format` into CI (currently unreferenced).

## Verification

- Python tests run locally.
- C tests + CI validated on JLSE / in the Actions runner (may need the Docker
  base image from Theme F).
