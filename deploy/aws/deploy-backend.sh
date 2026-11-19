#!/usr/bin/env bash
# Run on EC2 after git pull (also called from GitHub Actions). Idempotent.
set -euo pipefail

APP_DIR="${AFARM_BACKEND_DIR:-/srv/afarm/afarm-backend}"
cd "$APP_DIR"

git fetch origin main
git reset --hard origin/main

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart afarm-backend
else
  echo "systemctl not found — start uvicorn manually"
fi

echo "AFARM backend deploy done at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"