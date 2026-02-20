#!/usr/bin/env bats
# Integration test: Drava Python + JetStream (NATS)

bats_require_minimum_version 1.5.0

setup() {
  [[ -n "${ABS_TOP_SRCDIR:-}"  ]] || skip "ABS_TOP_SRCDIR not set"
  [[ -n "${ABS_TOP_BUILDDIR:-}" ]] || skip "ABS_TOP_BUILDDIR not set"
  # [[ "${USE_NATS:-0}" == "1" ]] || skip "Set USE_NATS=1 to enable JetStream integration test"


  command -v python3 >/dev/null 2>&1 || skip "python3 not found"
  command -v nats-server >/dev/null 2>&1 || skip "nats-server not found in PATH"

  export PYTHONUNBUFFERED=1
  export DRAVA_TRANSPORT="nats"
  export NATS_URL="nats://127.0.0.1:4222"

  # Make 'import drava' resolve from build tree
  export PYTHONPATH="${ABS_TOP_BUILDDIR}:${PYTHONPATH:-}"

  RUNPY="${ABS_TOP_SRCDIR}/examples/dataflow/app.py"
  PUB="${ABS_TOP_SRCDIR}/examples/dataflow/publisher_jetstream.py"
  REQ="${ABS_TOP_SRCDIR}/examples/dataflow/requirements.txt"

  [[ -f "$RUNPY" ]] || skip "missing $RUNPY"
  [[ -f "$PUB"  ]] || skip "missing $PUB"
  [[ -f "$REQ"  ]] || skip "missing $REQ"

  TDIR="${BATS_TEST_TMPDIR}/drava_js"
  mkdir -p "$TDIR/jsdata"

  export NATS_LOG="$TDIR/nats.log"
  export CONSUMER_LOG="$TDIR/consumer.log"
  export PUBLISHER_LOG="$TDIR/publisher.log"

  # Install deps into temp dir (no system pollution)
  export PYTHONPATH="$TDIR/pylibs:${PYTHONPATH}"
  python3 -m pip install -q --no-input --disable-pip-version-check \
    --target "$TDIR/pylibs" -r "$REQ" || skip "pip install failed"
    echo "PYTHONPATH=$PYTHONPATH" >&2
}

teardown() {
  if [[ -n "${CONSUMER_PID:-}" ]] && kill -0 "$CONSUMER_PID" 2>/dev/null; then
    kill "$CONSUMER_PID" 2>/dev/null || true
    wait "$CONSUMER_PID" 2>/dev/null || true
  fi
  if [[ -n "${NATS_PID:-}" ]] && kill -0 "$NATS_PID" 2>/dev/null; then
    kill "$NATS_PID" 2>/dev/null || true
    wait "$NATS_PID" 2>/dev/null || true
  fi
}

wait_for_log() {
  local file="$1"
  local pattern="$2"
  local timeout="${3:-15}"
  local end=$((SECONDS + timeout))
  while (( SECONDS < end )); do
    [[ -f "$file" ]] && grep -E "$pattern" "$file" >/dev/null && return 0
    sleep 0.2
  done
  return 1
}

die() {
  echo "ERROR: $*" >&2
  return 1
}

@test "jetstream: python consumer receives frame" {
  # Start NATS + JetStream
  nats-server -js -sd "$TDIR/jsdata" -a 127.0.0.1 -p 4222 >"$NATS_LOG" 2>&1 &
  NATS_PID=$!

  if ! wait_for_log "$NATS_LOG" "Listening for client connections" 10; then
    if grep -Ei "address already in use|bind:" "$NATS_LOG" >/dev/null 2>&1; then
      skip "port 4222 already in use"
    fi
    echo "---- nats log ----" >&2
    sed -n '1,200p' "$NATS_LOG" >&2
    die "nats-server did not start"
  fi

  # Start consumer
  python3 "$RUNPY" >"$CONSUMER_LOG" 2>&1 &
  CONSUMER_PID=$!

  sleep 1

  # Publish
  ( cd "$(dirname "$PUB")" && python3 "$PUB" ) >"$PUBLISHER_LOG" 2>&1

  # Assert receive
  if ! wait_for_log "$CONSUMER_LOG" "Python app received raw frame:" 15; then
    echo "---- consumer ----" >&2
    sed -n '1,250p' "$CONSUMER_LOG" >&2
    echo "---- publisher ----" >&2
    sed -n '1,250p' "$PUBLISHER_LOG" >&2
    echo "---- nats ----" >&2
    sed -n '1,250p' "$NATS_LOG" >&2
    die "consumer did not receive message"
  fi
}
