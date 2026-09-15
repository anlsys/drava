#!/usr/bin/env bash
# Run the PtychoPINN two-stage pipeline on a single JLSE A100 node.
#
# Launch order is downstream-first so no message is published before its
# consumer's durable exists: nats-server -> stage2 -> stage1 -> publisher.
#
# Prerequisites (see README.md):
#   - Drava built with NATS, build dir on PYTHONPATH
#   - example venv active, ptychopinn_torch installed
#   - python download_zenodo.py && python prepare_dataset.py
#
# Usage:
#   ./run_two_stages.sh
#   PTYCHOPINN_DATASET=W PTYCHOPINN_MODEL=PS_W ./run_two_stages.sh
#   DRAVA_PUBLISH_NUM_FRAMES=2000 ./run_two_stages.sh      # short smoke run

set -euo pipefail

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$EXAMPLE_DIR"

PYTHON="${PYTHON:-python3}"
NATS_SERVER="${NATS_SERVER:-nats-server}"
STAGE_CONFIG="${DRAVA_STAGE_CONFIG:-$EXAMPLE_DIR/pipeline.yaml}"
RUN_DIR="${RUN_DIR:-$EXAMPLE_DIR/run_logs/$(date +%Y%m%d_%H%M%S)}"
START_NATS="${START_NATS:-1}"
APP_TIMEOUT_S="${APP_TIMEOUT_S:-3600}"

export DRAVA_STAGE_CONFIG="$STAGE_CONFIG"

mkdir -p "$RUN_DIR"
echo "[run] example dir : $EXAMPLE_DIR"
echo "[run] stage config: $STAGE_CONFIG"
echo "[run] logs        : $RUN_DIR"

if [[ ! -f "$EXAMPLE_DIR/prep/${PTYCHOPINN_DATASET:-W}_${PTYCHOPINN_MODEL:-PS_W}/meta.json" ]]; then
  echo "[run] ERROR: prep artifacts missing. Run prepare_dataset.py first." >&2
  exit 1
fi

PIDS=()
cleanup() {
  local status=$?
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  exit "$status"
}
trap cleanup EXIT INT TERM

wait_for() {
  # wait_for <file> <pattern> <timeout_s> <label>
  local file="$1" pattern="$2" timeout="$3" label="$4"
  local waited=0
  while (( waited < timeout )); do
    if [[ -f "$file" ]] && grep -q "$pattern" "$file" 2>/dev/null; then
      echo "[run] $label ready"
      return 0
    fi
    sleep 1
    (( waited += 1 ))
  done
  echo "[run] ERROR: timed out waiting for $label ('$pattern' in $file)" >&2
  tail -n 40 "$file" >&2 2>/dev/null || true
  return 1
}

if [[ "$START_NATS" == "1" ]]; then
  echo "[run] starting nats-server"
  rm -rf "$EXAMPLE_DIR/jsdata"
  "$NATS_SERVER" -c "$EXAMPLE_DIR/nats.conf" >"$RUN_DIR/nats.log" 2>&1 &
  PIDS+=("$!")
  wait_for "$RUN_DIR/nats.log" "Listening for client connections" 30 "nats-server"
fi

echo "[run] starting stage2"
DRAVA_STAGE_NAME=stage2 \
DRAVA_METRICS_FILE="$RUN_DIR/metrics_stage2.jsonl" \
  "$PYTHON" app_stage2.py >"$RUN_DIR/app_stage2.log" 2>&1 &
STAGE2_PID=$!
PIDS+=("$STAGE2_PID")
wait_for "$RUN_DIR/app_stage2.log" "JetStream ready:" 600 "stage2"

echo "[run] starting stage1"
DRAVA_STAGE_NAME=stage1 \
DRAVA_METRICS_FILE="$RUN_DIR/metrics_stage1.jsonl" \
  "$PYTHON" app.py >"$RUN_DIR/app_stage1.log" 2>&1 &
STAGE1_PID=$!
PIDS+=("$STAGE1_PID")
wait_for "$RUN_DIR/app_stage1.log" "JetStream ready:" 900 "stage1"

echo "[run] starting publisher"
DRAVA_PUBLISHER_METRICS_FILE="$RUN_DIR/pub_metrics.json" \
  "$PYTHON" publisher_jetstream.py >"$RUN_DIR/pub.log" 2>&1
echo "[run] publisher finished"

echo "[run] waiting for stages to drain (timeout ${APP_TIMEOUT_S}s)"
waited=0
while (( waited < APP_TIMEOUT_S )); do
  if ! kill -0 "$STAGE2_PID" 2>/dev/null; then
    break
  fi
  sleep 2
  (( waited += 2 ))
done

wait "$STAGE1_PID" 2>/dev/null || true
wait "$STAGE2_PID" 2>/dev/null || true

echo
echo "[run] ---------------- result ----------------"
grep -h "\[stage2-final\]" "$RUN_DIR/app_stage2.log" || {
  echo "[run] ERROR: no [stage2-final] line; see $RUN_DIR/app_stage2.log" >&2
  exit 1
}
echo "[run] logs in $RUN_DIR"
