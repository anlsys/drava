# Theme E — Recoverable errors (embeddability)

Date: 2026-07-13
Status: Proposed
Impact: Medium · Effort: M · Local: No (JLSE)
Index: [2026-07-13-roadmap.md](2026-07-13-roadmap.md)

## Context

13 `LOGGER_FATAL` vs 7 `LOGGER_ERROR` in `src/*.cc`. A missing socket
([src/transport_socket.cc:88](../src/transport_socket.cc#L88)), socket
open/connect failure (`:92`/`:101`), or NATS connect/subscribe/fetch failure
([src/transport_js.cc:176,187,238,322](../src/transport_js.cc#L176)) **aborts the
whole process** rather than returning `DRAVA_ERROR`. The pattern is inconsistent
even within `transport_socket.cc` (the publish path correctly returns
`DRAVA_ERROR` for a missing FIFO at `:53`/`:58`). This makes drava unusable as an
embeddable library — a caller can't catch a bad path or a down broker.

## Fix

- Convert setup/connection `LOGGER_FATAL` on the ingress path to `LOGGER_ERROR` +
  propagate `DRAVA_ERROR` up through `drava_transport_*_main` → `listen()` →
  `drava_listen_py()` so Python sees a non-success rc instead of a crash.
- Improve the two terse messages: fix the socket "does not exists" typo and add a
  hint to start socat/publisher; print the offending YAML transport string, not
  the raw enum ([src/drava.cc:40](../src/drava.cc#L40)).

## Files to modify

- [../src/transport_socket.cc](../src/transport_socket.cc),
  [../src/transport_js.cc](../src/transport_js.cc),
  [../src/drava.cc](../src/drava.cc) (error propagation through `listen`).

## Verification

- JLSE: point a stage at a nonexistent socket / down NATS and confirm `listen()`
  returns an error and the process exits cleanly instead of aborting.
