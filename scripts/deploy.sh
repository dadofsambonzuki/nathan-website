#!/bin/bash
set -euo pipefail

PROD_DIR="/var/www/nathan.day.ag"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=== Starting deployment ==="
echo ""

git pull --rebase=false
python3 scripts/fetch_nostr_events.py
hugo --minify
sudo rsync -av --delete public/ "$PROD_DIR/"

echo ""
echo "=== Deployment complete ==="
