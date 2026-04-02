#!/bin/bash
# Deploy script for nathan-website
# Detects if running locally on VPS or remotely, and runs accordingly

set -e

VPS_HOST="vps"
VPS_USER="ubuntu"
VPS_PATH="/home/ubuntu/nathan-website"
PROD_DIR="/var/www/nathan.day.ag"

check_if_vps() {
    if [[ -d "$VPS_PATH/.git" ]]; then
        remote_url=$(git remote get-url origin 2>/dev/null || echo "")
        if [[ "$remote_url" == *"dadofsambonzuki/nathan-website"* ]]; then
            return 0  # True - running on VPS
        fi
    fi
    return 1  # False - running remotely
}

echo "=== Starting deployment ==="
echo ""

if check_if_vps; then
    echo ">>> Running locally on VPS..."
    git pull --rebase=false
    python3 scripts/fetch_nostr_events.py
    hugo --minify
    sudo rsync -av --delete public/ "$PROD_DIR/"
else
    echo ">>> Deploying remotely to VPS ($VPS_HOST)..."
    ssh "$VPS_HOST" "cd $VPS_PATH && git pull --rebase=false && python3 scripts/fetch_nostr_events.py && hugo --minify && sudo rsync -av --delete public/ $PROD_DIR/"
fi

echo ""
echo "=== Deployment complete ==="
