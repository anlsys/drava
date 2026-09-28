#!/usr/bin/env bats
# Regression test: drava_frame_batch_t::base_index must be assigned in message
# ARRIVAL order, not in worker-task execution order.
#
# Background. The runtime reserves a batch's global frame indices with
#   next_data_index.fetch_add(data_frame_count)
# If that reservation happens inside the task spawned by the transport
# (callback_serialize: false), concurrent callbacks are numbered in
# task-execution order, so a batch can receive a LOWER base_index than a batch
# that arrived before it. The frame COUNT stays correct, so no accounting
# check catches it; only the association between a frame and its stream
# position is wrong. Apps that place results by base_index (e.g.
# examples/ptychonn/app_stage2.py) then write to the wrong positions.
#
# This test makes each frame carry its own stream position, so the app can
# check base_index against ground truth directly.
#
# NOTE: the config deliberately uses threads: 4 + callback_serialize: false.
# Do not "fix" a failure by serializing callbacks; that hides the defect.

bats_require_minimum_version 1.5.0

setup() {
  [[ -n "${ABS_TOP_SRCDIR:-}"  ]] || skip "ABS_TOP_SRCDIR not set"
  [[ -n "${ABS_TOP_BUILDDIR:-}" ]] || skip "ABS_TOP_BUILDDIR not set"

  command -v python3 >/dev/null 2>&1 || skip "python3 not found"
  command -v socat   >/dev/null 2>&1 || skip "socat not found"

  export PYTHONUNBUFFERED=1
  export DRAVA_STAGE_CONFIG="${ABS_TOP_SRCDIR}/tests/base_index_ordering.yaml"
  export DRAVA_STAGE_NAME="test_stage"
  export PYTHONPATH="${ABS_TOP_BUILDDIR}:${PYTHONPATH:-}"

  APP="${ABS_TOP_SRCDIR}/tests/integration/base_index_ordering_app.py"
  PUB="${ABS_TOP_SRCDIR}/tests/integration/base_index_ordering_publisher.py"
  [[ -f "$APP" ]] || skip "missing $APP"
  [[ -f "$PUB" ]] || skip "missing $PUB"
  [[ -f "$DRAVA_STAGE_CONFIG" ]] || skip "missing $DRAVA_STAGE_CONFIG"

  export DRAVA_FIFO_PATH="${BATS_TEST_TMPDIR}/drava_baseidx_in"
  export DRAVA_SOCKET_PATH="${BATS_TEST_TMPDIR}/drava_baseidx.sock"
  export DRAVA_TEST_NUM_FRAMES="${DRAVA_TEST_NUM_FRAMES:-4096}"

  TDIR="${BATS_TEST_TMPDIR}/work"
  mkdir -p "$TDIR"
  export APP_LOG="$TDIR/app.log"
  export PUB_LOG="$TDIR/pub.log"

  mkfifo "$DRAVA_FIFO_PATH"
  socat "$DRAVA_FIFO_PATH" UNIX-LISTEN:"$DRAVA_SOCKET_PATH",fork \
    >"$TDIR/socat.out" 2>"$TDIR/socat.err" &
  SOCAT_PID=$!

  for _ in {1..50}; do
    [[ -S "$DRAVA_SOCKET_PATH" ]] && break
    sleep 0.1
  done
  [[ -S "$DRAVA_SOCKET_PATH" ]] || skip "socket not created: $DRAVA_SOCKET_PATH"
}

teardown() {
  [[ -n "${APP_PID:-}"   ]] && kill "$APP_PID"   2>/dev/null || true
  [[ -n "${SOCAT_PID:-}" ]] && kill "$SOCAT_PID" 2>/dev/null || true
  rm -f "${DRAVA_FIFO_PATH:-}" "${DRAVA_SOCKET_PATH:-}" 2>/dev/null || true
}

@test "base_index is assigned in arrival order under parallel callbacks" {
  python3 "$APP" >"$APP_LOG" 2>&1 &
  APP_PID=$!

  # Wait for the stage to be listening before feeding the FIFO.
  for _ in {1..100}; do
    grep -q "Connected to socket" "$APP_LOG" 2>/dev/null && break
    sleep 0.1
  done

  run python3 "$PUB"
  [ "$status" -eq 0 ] || { cat "$PUB_LOG" 2>/dev/null; echo "$output"; false; }

  # Wait for the end-of-stream summary.
  for _ in {1..200}; do
    grep -q "\[base-index-test\]" "$APP_LOG" 2>/dev/null && break
    sleep 0.1
  done

  run grep -h "\[base-index-test\]" "$APP_LOG"
  if [ "$status" -ne 0 ]; then
    echo "--- app log ---"; cat "$APP_LOG"
    false
  fi
  echo "summary: $output"

  # The invariant: every frame's declared position equals base_index + offset.
  [[ "$output" == *"mismatches=0"* ]] || {
    echo "FAIL: base_index did not match the frames' true stream positions."
    echo "This is the parallel-callback ordering defect; base_index must be"
    echo "reserved in the transport fetch loop, not inside the spawned task."
    echo "--- app log ---"; cat "$APP_LOG"
    false
  }

  # And no frame may be lost, duplicated, or truncated.
  [[ "$output" == *"coverage_ok=1"*        ]] || { cat "$APP_LOG"; false; }
  [[ "$output" == *"short_payloads=0"*     ]] || { cat "$APP_LOG"; false; }
  [[ "$output" == *"frames=${DRAVA_TEST_NUM_FRAMES}"* ]] || { cat "$APP_LOG"; false; }
}
