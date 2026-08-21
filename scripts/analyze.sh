#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${MAKER_EDGE_LOG_DIR:-$ROOT/logs/maker_edge}"
# Prefer project venv python if present
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PY" "$ROOT/scripts/analyze_maker_edge.py" --dir "$LOG_DIR" --report --min-fills "${1:-2000}"
