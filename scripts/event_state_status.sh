#!/usr/bin/env bash
# Remote EXP_002 long-run status (read-only). Does not analyze Path C.
set -euo pipefail

SSH_HOST="${SSH_HOST:-jack@jackyu66.com}"
SSH_KEY="${SSH_KEY:-${HOME}/Project/deploy/zun_hk/id_ed25519_hk}"
REMOTE_DIR="${REMOTE_DIR:-/www/Project/nautilus_mm}"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
if [[ -n "$SSH_KEY" ]]; then
  chmod 400 "$SSH_KEY" 2>/dev/null || true
  SSH_OPTS+=(-i "$SSH_KEY")
fi

ssh "${SSH_OPTS[@]}" "$SSH_HOST" "REMOTE_DIR='$REMOTE_DIR' bash -s" <<'EOF'
set -euo pipefail
echo "=== systemd --user event-state-probe ==="
systemctl --user is-active event-state-probe || true
systemctl --user show event-state-probe -p Environment --no-pager 2>/dev/null | tr ' ' '\n' | grep -E 'ENABLE_TRADING|EXPERIMENT_ID|LEDGER_RUN_ID' || true
echo ""
echo "=== mm-edge-probe (EXP_001) ==="
systemctl --user is-active mm-edge-probe || true
echo ""
LOG="$REMOTE_DIR/logs/event_state/EXP-002-RUN-002"
echo "=== ledger $LOG ==="
if [[ ! -d "$LOG" ]]; then
  echo "no log dir yet"
  exit 0
fi
python3 - <<PY
import json
from pathlib import Path
log = Path("$LOG")
starts = trades = books = fills = parse_fail = 0
run_id = None
for f in sorted(log.glob("*.jsonl")):
    for line in f.open():
        s = line.strip()
        if not s:
            continue
        try:
            ev = json.loads(s)
        except Exception:
            parse_fail += 1
            continue
        run_id = ev.get("run_id") or run_id
        e = ev.get("event")
        if e == "experiment_start":
            starts += 1
        elif e == "fill_anchor":
            fills += 1
        elif e == "market_event":
            t = ev.get("event_type")
            if t == "aggressive_trade":
                trades += 1
            elif t == "book_update":
                books += 1
print(f"run_id={run_id} starts={starts} trades={trades} books={books} fill_anchors={fills} parse_fail={parse_fail}")
print("Gate 4 remains BLOCKED until fill_anchors exist. Do not Path-C snoop.")
PY
echo ""
echo "=== journal (last 15) ==="
journalctl --user -u event-state-probe -n 15 --no-pager || true
EOF
