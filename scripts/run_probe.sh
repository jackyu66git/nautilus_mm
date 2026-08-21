#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r requirements.txt
fi

# shellcheck disable=SC1091
source .venv/bin/activate
export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# 本地可开代理；服务器 systemd 直连，勿强制 7897
if [[ "${USE_PROXY:-}" == "1" || "${USE_PROXY:-}" == "true" ]]; then
  export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7897}"
  export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7897}"
  echo "[run_probe] proxy=$HTTPS_PROXY"
elif [[ -n "${HTTPS_PROXY:-}${HTTP_PROXY:-}" ]]; then
  echo "[run_probe] proxy=${HTTPS_PROXY:-$HTTP_PROXY}"
else
  echo "[run_probe] direct (no proxy)"
fi

exec python -m nautilus_mm.run_live
