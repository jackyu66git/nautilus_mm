#!/usr/bin/env bash
# 远程查看探针状态 + fills/clusters 粗计数
# 用法：export SSH_HOST=user@ip  [SSH_KEY=...]  ./scripts/probe_status.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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
echo "=== systemd --user ==="
systemctl --user is-active mm-edge-probe || true
systemctl --user status mm-edge-probe --no-pager -l | head -20 || true
echo ""
echo "=== experiment (.env) ==="
grep -E '^(EXPERIMENT_ID|PROBE_VERSION|BINANCE_ENVIRONMENT|ENABLE_TRADING)=' "$REMOTE_DIR/.env" 2>/dev/null || true
grep -E '^BINANCE_API_KEY=.+' "$REMOTE_DIR/.env" >/dev/null && echo "API key: SET" || echo "API key: EMPTY"
echo ""
echo "=== fills / clusters (jsonl) ==="
cd "$REMOTE_DIR/logs/maker_edge" 2>/dev/null || { echo "no log dir"; exit 0; }
python3 - <<'PY'
import json
from pathlib import Path
fills=0
cids=set()
health=0
for f in sorted(Path('.').glob('*.jsonl')):
    for line in f.read_text().splitlines():
        try:
            ev=json.loads(line)
        except Exception:
            continue
        if ev.get('event')=='fill':
            fills+=1
            if ev.get('event_cluster_id'):
                cids.add(ev['event_cluster_id'])
        elif ev.get('event')=='health':
            health+=1
print(f"fills={fills}  clusters={len(cids)}  health_ticks={health}")
print(f"cluster/fill={len(cids)/fills*100:.1f}%" if fills else "cluster/fill=n/a")
PY
echo ""
echo "=== recent journal (--user) ==="
journalctl --user -u mm-edge-probe -n 30 --no-pager || true
EOF
