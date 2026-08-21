#!/usr/bin/env bash
# MM_EDGE_EXP_002 smoke test — 10–15 min, restart in the middle, NO trading.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RUN_ID="${LEDGER_RUN_ID:-EXP-002-RUN-001}"
SESSION_SECS="${SESSION_SECS:-360}"   # 6 min × 2 = 12 min collect
LOG_DIR="${EVENT_STATE_LOG_DIR:-$ROOT/logs/event_state/$RUN_ID}"
PYTHON="${ROOT}/.venv/bin/python"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export EXPERIMENT_ID=MM_EDGE_EXP_002
export PROBE_VERSION=event_state_v0.1
export ENABLE_TRADING=false
export LEDGER_RUN_ID="$RUN_ID"
export EVENT_STATE_LOG_DIR="$LOG_DIR"
export PYTHONPATH="$ROOT/src"

mkdir -p "$LOG_DIR"

run_session() {
  local label="$1"
  export LEDGER_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
  echo "[smoke] session ${label} start session_id=${LEDGER_SESSION_ID} secs=${SESSION_SECS}"
  "$PYTHON" -m nautilus_mm.run_event_state &
  local pid=$!
  echo "[smoke] pid=${pid}"
  sleep "$SESSION_SECS"
  echo "[smoke] session ${label} stopping pid=${pid}"
  kill -INT "$pid" 2>/dev/null || true
  # allow experiment_stop flush
  local i=0
  while kill -0 "$pid" 2>/dev/null && [[ $i -lt 30 ]]; do
    sleep 1
    i=$((i + 1))
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "[smoke] SIGINT timeout — SIGTERM"
    kill -TERM "$pid" 2>/dev/null || true
    sleep 3
  fi
  if kill -0 "$pid" 2>/dev/null; then
    echo "[smoke] SIGTERM timeout — SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
  fi
  wait "$pid" 2>/dev/null || true
  echo "[smoke] session ${label} stopped"
}

echo "[smoke] RUN_ID=${RUN_ID} log=${LOG_DIR} trading=NO"
run_session A
echo "[smoke] restart gap 5s"
sleep 5
run_session B

echo "[smoke] validating ledger"
"$PYTHON" "$ROOT/scripts/validate_event_ledger.py" \
  --dir "$LOG_DIR" \
  --run-id "$RUN_ID" \
  --out "$LOG_DIR/Event_Ledger_Validation.json"
echo "[smoke] done"
