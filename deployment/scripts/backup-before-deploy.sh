#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — backup-before-deploy.sh
# Phase 23: Dump a compressed Postgres snapshot before deploying.
# Usage: bash deployment/scripts/backup-before-deploy.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/pre_deploy_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"
echo "Creating database backup: $FILE"

docker compose \
  -f "$REPO_ROOT/docker-compose.yml" \
  -f "$REPO_ROOT/docker-compose.prod.yml" \
  exec -T postgres pg_dump \
  -U "${DB_USER:-restaurantflow}" \
  -d "${DB_NAME:-restaurantflow}" \
  | gzip > "$FILE"

echo "Backup complete: $FILE"

# Retain only the 7 most recent backups
ls -t "$BACKUP_DIR"/pre_deploy_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm --
echo "Old backups pruned (keeping 7 most recent)"
