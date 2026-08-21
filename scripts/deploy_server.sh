#!/usr/bin/env bash
# 部署 MM_EDGE_EXP_001 → jack@jackyu66.com:/www/Project/nautilus_mm
#
# 默认：
#   SSH_HOST=jack@jackyu66.com
#   SSH_KEY=~/Project/deploy/zun_hk/id_ed25519_hk
#   REMOTE_DIR=/www/Project/nautilus_mm
#
# 覆盖：export SSH_HOST=... SSH_KEY=... REMOTE_DIR=...
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SSH_HOST="${SSH_HOST:-jack@jackyu66.com}"
SSH_KEY="${SSH_KEY:-${HOME}/Project/deploy/zun_hk/id_ed25519_hk}"
REMOTE_DIR="${REMOTE_DIR:-/www/Project/nautilus_mm}"

if [[ ! -f "$SSH_KEY" ]]; then
  echo "SSH key not found: $SSH_KEY"
  exit 1
fi
chmod 400 "$SSH_KEY" 2>/dev/null || true

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)
SSH=(ssh "${SSH_OPTS[@]}" "$SSH_HOST")
RSYNC_E="ssh ${SSH_OPTS[*]}"

echo "==> stop remote probe before sync (if running)"
"${SSH[@]}" "systemctl --user stop mm-edge-probe 2>/dev/null || true"

echo "==> sync $ROOT → $SSH_HOST:$REMOTE_DIR"
"${SSH[@]}" "mkdir -p '$REMOTE_DIR' '$REMOTE_DIR/logs/maker_edge'"
rsync -avz --delete \
  -e "$RSYNC_E" \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'logs/maker_edge/*.jsonl' \
  --exclude 'logs/maker_edge/*.txt' \
  --exclude 'logs/maker_edge_smoke' \
  --exclude '.env' \
  "$ROOT/" "$SSH_HOST:$REMOTE_DIR/"

echo "==> remote setup (uv venv + user systemd)"
"${SSH[@]}" "REMOTE_DIR='$REMOTE_DIR' bash -s" <<'REMOTE'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$REMOTE_DIR"
if [[ ! -f .env ]]; then
  cp .env.example .env
  {
    echo ""
    echo "# Server Data Collection — MM_EDGE_EXP_001"
    echo "EXPERIMENT_ID=MM_EDGE_EXP_001"
    echo "PROBE_VERSION=probe_v0.1"
    echo "EXCHANGE_NAME=binance_usdm"
    echo "BINANCE_ENVIRONMENT=TESTNET"
    echo "ENABLE_TRADING=false"
    echo "QUOTE_TTL_SECS=30"
    echo "MAX_ABS_INVENTORY=0.005"
    echo "HTTP_PROXY="
    echo "HTTPS_PROXY="
    echo "MAKER_EDGE_LOG_DIR=${REMOTE_DIR}/logs/maker_edge"
  } >> .env
  echo "CREATED .env — fill BINANCE_API_KEY / BINANCE_API_SECRET"
else
  echo ".env exists — left untouched"
fi

if [[ ! -x "$HOME/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv python install 3.12
rm -rf .venv
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv/bin/python

mkdir -p "$HOME/.config/systemd/user"
sed -e "s|/www/Project/nautilus_mm|${REMOTE_DIR}|g" \
  deploy/mm-edge-probe.user.service > "$HOME/.config/systemd/user/mm-edge-probe.service"
systemctl --user daemon-reload
systemctl --user enable mm-edge-probe.service
loginctl enable-linger "$(whoami)" 2>/dev/null || true
echo "User systemd installed (not started — fill keys first)."
echo "  nano $REMOTE_DIR/.env"
echo "  systemctl --user start mm-edge-probe"
echo "  journalctl --user -u mm-edge-probe -f"
REMOTE

echo ""
echo "==> done"
echo "1) ssh -i $SSH_KEY $SSH_HOST"
echo "2) nano $REMOTE_DIR/.env   # TESTNET keys"
echo "3) systemctl --user start mm-edge-probe"
echo "4) ./scripts/probe_status.sh"
echo "5) ./scripts/pull_report.sh"
