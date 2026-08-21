#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Preserve systemd/caller identity before .env (which still belongs to EXP_001)
PRESERVE_RUN_ID="${LEDGER_RUN_ID:-}"
PRESERVE_LOG_DIR="${EVENT_STATE_LOG_DIR:-}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# Layer 1 (script): force EXP_002 contract after .env
export EXPERIMENT_ID=MM_EDGE_EXP_002
export PROBE_VERSION=event_state_v0.1
export ENABLE_TRADING=false
export LEDGER_RUN_ID="${PRESERVE_RUN_ID:-${LEDGER_RUN_ID:-EXP-002-RUN-002}}"
export EVENT_STATE_LOG_DIR="${PRESERVE_LOG_DIR:-$ROOT/logs/event_state/$LEDGER_RUN_ID}"
export PYTHONPATH="${PYTHONPATH:-$ROOT/src}"
mkdir -p "$EVENT_STATE_LOG_DIR"

echo "[run_event_state] EXP_002 observability | trading=NO | run=$LEDGER_RUN_ID | log=$EVENT_STATE_LOG_DIR"
exec "$ROOT/.venv/bin/python" -m nautilus_mm.run_event_state
