#!/bin/bash
# Deploy script for nathan-website
# SSH to VPS, pulls latest, builds Hugo site, and copies to production

set -e

VPS_HOST="vps"

echo "=== Starting deployment ==="
echo ""

# SSH to VPS and run deployment
echo ">>> Deploying to VPS ($VPS_HOST)..."
ssh "$VPS_HOST" "cd /home/ubuntu/nathan-website && git pull --rebase=false && python3 scripts/fetch_nostr_events.py && hugo --minify && sudo rsync -av --delete public/ /var/www/nathan.day.ag/"
echo ""

echo "=== Deployment complete ==="
