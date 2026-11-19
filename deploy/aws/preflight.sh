#!/usr/bin/env bash
# Run on EC2 after SSH: bash preflight.sh
# Checks tools and memory before AFARM install (khulega-online / Amazon Linux 2023).

set -euo pipefail

echo "=== Host ==="
hostname
whoami
uname -a

echo ""
echo "=== Memory & disk ==="
free -h || true
df -h / /srv 2>/dev/null || df -h /

echo ""
echo "=== Listening web ports (sample) ==="
sudo ss -tlnp 2>/dev/null | head -20 || ss -tlnp | head -20

echo ""
echo "=== Commands ==="
for cmd in git python3 node npm nginx psql; do
  if command -v "$cmd" >/dev/null; then
    echo "  OK  $cmd → $(command -v "$cmd") ($($cmd --version 2>&1 | head -1))"
  else
    echo "  MISSING  $cmd"
  fi
done

echo ""
echo "=== AFARM dirs ==="
for d in /srv/afarm/afarm-backend /srv/afarm/afarm-frontend; do
  if [[ -d "$d" ]]; then echo "  exists: $d"; else echo "  not yet: $d"; fi
done

if [[ $(free -m 2>/dev/null | awk '/^Mem:/{print $2}') -lt 900 ]]; then
  echo ""
  echo "⚠ Low RAM detected. For Next.js build on t3.nano, consider swap:"
  echo "  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
  echo "  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab"
fi

echo ""
echo "Done. Next: Route 53 → deploy/aws/README.md"