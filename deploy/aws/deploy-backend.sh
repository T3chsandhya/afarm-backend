#!/usr/bin/env bash
# Run on EC2 after git pull (also called from GitHub Actions). Idempotent.
set -euo pipefail

APP_DIR="${AFARM_BACKEND_DIR:-/srv/afarm/afarm-backend}"
cd "$APP_DIR"

git fetch origin main
git reset --hard origin/main

pick_python() {
  local bin
  for bin in python3.11 python3.12 python3.13 python3; do
    if command -v "$bin" >/dev/null 2>&1 && "$bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
      echo "$bin"
      return 0
    fi
  done
  echo "ERROR: Python 3.10+ required (install python3.11: sudo dnf install -y python3.11)." >&2
  return 1
}

PYTHON_BIN="$(pick_python)"

venv_needs_rebuild() {
  [[ ! -d .venv ]] && return 0
  if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    return 0
  fi
  return 1
}

if venv_needs_rebuild; then
  echo "Creating venv with ${PYTHON_BIN} …"
  rm -rf .venv
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -V
pip install -q -r requirements.txt

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart afarm-backend
else
  echo "systemctl not found — start uvicorn manually"
fi

echo "AFARM backend deploy done at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"