#!/usr/bin/env bats
# Integration test: Drava Python + socket transport (FIFO -> socat -> UNIX socket)

bats_require_minimum_version 1.5.0

setup() {
  [[ -n "${ABS_TOP_SRCDIR:-}"  ]] || skip "ABS_TOP_SRCDIR not set"
  [[ -n "${ABS_TOP_BUILDDIR:-}" ]] || skip "ABS_TOP_BUILDDIR not set"

  command -v python3 >/dev/null 2>&1 || skip "python3 not found"
  command -v socat   >/dev/null 2>&1 || skip "socat not found"

  export PYTHONUNBUFFERED=1
  export DRAVA_TRANSPORT="socket"

  # Make 'import drava' resolve from build tree
  export PYTHONPATH="${ABS_TOP_BUILDDIR}:${PYTHONPATH:-}"

  RUNPY="${ABS_TOP_SRCDIR}/examples/dataflow/run.py"
  PUB="${ABS_TOP_SRCDIR}/examples/dataflow/publisher_socket.py"
  REQ="${ABS_TOP_SRCDIR}/examples/dataflow/requirements.txt"
  [[ -f "$RUNPY" ]] || skip "missing $RUNPY"
  [[ -f "$PUB"  ]] || skip "missing $PUB"
  [[ -f "$REQ" ]] || skip "missing $REQ"

  export PYTHONPATH="$TDIR/pylibs:${PYTHONPATH:-}"
  python3 -m pip install -q --no-input --disable-pip-version-check \
    --target "$TDIR/pylibs" -r "$REQ" || skip "pip install failed"

  # Paths used by your publisher + drava socket transport
  export DRAVA_FIFO_PATH="${DRAVA_FIFO_PATH:-/tmp/drava_in}"
  export DRAVA_SOCKET_PATH="${DRAVA_SOCKET_PATH:-/tmp/accel_2048.sock}"

  rm -f "$DRAVA_FIFO_PATH" "$DRAVA_SOCKET_PATH"
  mkfifo "$DRAVA_FIFO_PATH"

  TDIR="${BATS_TEST_TMPDIR}/drava_sock"
  mkdir -p "$TDIR"

  export SOCAT_OUT="$TDIR/socat.out"
  export SOCAT_ERR="$TDIR/socat.err"
  export CONSUMER_LOG="$TDIR/consumer.log"
  export PUBLISHER_LOG="$TDIR/publisher.log"


  # FIFO -> UNIX socket bridge
  socat "$DRAVA_FIFO_PATH" UNIX-LISTEN:"$DRAVA_SOCKET_PATH",fork \
    >"$SOCAT_OUT" 2>"$SOCAT_ERR" &
  SOCAT_PID=$!

  # Wait for socket creation
  for i in {1..50}; do
    [[ -S "$DRAVA_SOCKET_PATH" ]] && break
    sleep 0.1
  done
  [[ -S "$DRAVA_SOCKET_PATH" ]] || skip "socket was not created: $DRAVA_SOCKET_PATH"
}

teardown() {
  if [[ -n "${CONSUMER_PID:-}" ]] && kill -0 "$CONSUMER_PID" 2>/dev/null; then
    kill "$CONSUMER_PID" 2>/dev/null || true
    wait "$CONSUMER_PID" 2>/dev/null || true
  fi

  if [[ -n "${SOCAT_PID:-}" ]] && kill -0 "$SOCAT_PID" 2>/dev/null; then
    kill "$SOCAT_PID" 2>/dev/null || true
    wait "$SOCAT_PID" 2>/dev/null || true
  fi

  rm -f "$DRAVA_FIFO_PATH" "$DRAVA_SOCKET_PATH"
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

@test "socket: python consumer receives one frame via FIFO+socat" {
  python3 "$RUNPY" >"$CONSUMER_LOG" 2>&1 &
  CONSUMER_PID=$!

  sleep 0.5

  # Deterministic publish once
  SEND_ONCE=1 python3 "$PUB" >"$PUBLISHER_LOG" 2>&1

  if ! wait_for_log "$CONSUMER_LOG" "Python app received:" 10; then
    echo "---- consumer ----" >&2
    sed -n '1,250p' "$CONSUMER_LOG" >&2
    echo "---- publisher ----" >&2
    sed -n '1,250p' "$PUBLISHER_LOG" >&2
    echo "---- socat out ----" >&2
    sed -n '1,250p' "$SOCAT_OUT" >&2
    echo "---- socat err ----" >&2
    sed -n '1,250p' "$SOCAT_ERR" >&2
    die "consumer did not receive message"
  fi
}