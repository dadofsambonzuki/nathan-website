#!/bin/bash
# Deploy script for nathan-website
# Runs nostr sync, builds Hugo site, and copies to production

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROD_DIR="/var/www/nathan.day.ag"

cd "$PROJECT_DIR"

echo "=== Starting deployment ==="
echo ""

# Step 1: Run nostr sync
echo ">>> Running nostr sync..."
python3 scripts/fetch_nostr_events.py
echo ""

# Step 2: Build Hugo site
echo ">>> Building Hugo site..."
hugo --minify
echo ""

# Step 3: Copy to production
echo ">>> Copying to production ($PROD_DIR)..."
sudo rsync -av --delete public/ "$PROD_DIR/"
echo ""

echo "=== Deployment complete ==="
