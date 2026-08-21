#!/usr/bin/env bash
# 从服务器拉取 jsonl + 本地生成 Maker Edge Report
# 用法：export SSH_HOST=user@ip  [SSH_KEY=...]  ./scripts/pull_report.sh [min_fills]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_HOST="${SSH_HOST:-jack@jackyu66.com}"
SSH_KEY="${SSH_KEY:-${HOME}/Project/deploy/zun_hk/id_ed25519_hk}"
REMOTE_DIR="${REMOTE_DIR:-/www/Project/nautilus_mm}"
LOCAL_LOG="${LOCAL_LOG:-$ROOT/logs/maker_edge}"

SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
if [[ -n "$SSH_KEY" ]]; then
  chmod 400 "$SSH_KEY" 2>/dev/null || true
  SSH_OPTS+=(-i "$SSH_KEY")
fi

mkdir -p "$LOCAL_LOG"
echo "==> pull logs from $SSH_HOST"
rsync -avz -e "ssh ${SSH_OPTS[*]}" \
  "$SSH_HOST:$REMOTE_DIR/logs/maker_edge/" "$LOCAL_LOG/"

echo "==> analyze"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$ROOT/scripts/analyze.sh" "${1:-2000}"
