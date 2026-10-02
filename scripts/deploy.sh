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
# Resolve the npub/nprofile mentions to profile names for the templates. A
# relay failure must not block the deploy: the templates fall back to a
# shortened identifier, so warn and carry on.
python3 scripts/resolve_nostr_mentions.py --verbose || echo "Warning: Nostr mention resolution failed, keeping cached names"
hugo --minify
sudo rsync -av --delete public/ "$PROD_DIR/"

echo ""
echo "=== Deployment complete ==="
