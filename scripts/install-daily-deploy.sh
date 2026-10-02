#!/bin/bash
#
# Install (or refresh) the daily deploy cron job on the VPS.
#
# Runs scripts/deploy.sh as the repository's owner — the same user the GitHub
# self-hosted runner uses — so git, the Nostr sync and hugo all see the same
# HOME, SSH keys and permissions. deploy.sh's sudo rsync works because the
# runner user has passwordless sudo (that is already how a push deploy works).
#
# Usage:  scripts/install-daily-deploy.sh
#         SCHEDULE="*/5 * * * *" scripts/install-daily-deploy.sh   # for testing
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRON_FILE="/etc/cron.d/nathan-website"
LOG_FILE="/var/log/nathan-website-deploy.log"
SCHEDULE="${SCHEDULE:-17 6 * * *}"

if [ "$(id -u)" -eq 0 ]; then
  echo "install-daily-deploy: run as the repository owner; the script uses sudo where it needs it" >&2
  exit 1
fi

DEPLOY_USER="$(stat -c %U "$REPO_DIR")"
HOME_DIR="$(getent passwd "$DEPLOY_USER" | cut -d: -f6)"

echo "=== Installing the daily deploy cron job ==="
echo "repo:     $REPO_DIR"
echo "user:     $DEPLOY_USER"
echo "schedule: $SCHEDULE"

sudo tee "$CRON_FILE" >/dev/null <<EOF
# Daily deploy of nathan.day.ag: pulls the Nostr notes and articles, resolves
# the mentions, rebuilds and rsyncs to /var/www/nathan.day.ag.
# Managed by $REPO_DIR/scripts/install-daily-deploy.sh — edit there, not here.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=$HOME_DIR
MAILTO=""
$SCHEDULE $DEPLOY_USER $REPO_DIR/scripts/deploy.sh >> $LOG_FILE 2>&1
EOF

sudo chmod 0644 "$CRON_FILE"

if [ ! -f "$LOG_FILE" ]; then
  sudo touch "$LOG_FILE"
  sudo chown "$DEPLOY_USER" "$LOG_FILE"
fi

echo ""
echo "--- $CRON_FILE ---"
cat "$CRON_FILE"
echo "--- cron service ---"
systemctl is-active cron 2>/dev/null || systemctl is-active crond 2>/dev/null || echo "no cron service found"
echo "--- next scheduled runs ---"
sudo systemctl list-timers 2>/dev/null | head -3 || true
echo ""
echo "Logs: $LOG_FILE"
