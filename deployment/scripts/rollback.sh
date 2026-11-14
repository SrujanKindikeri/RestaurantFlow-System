#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — rollback.sh
# Phase 23: Pull a previous image tag and restart services.
# Usage: bash deployment/scripts/rollback.sh <previous-image-tag>
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PREV_TAG="${1:?Usage: rollback.sh <previous-image-tag>}"

echo "=== Rolling back to: $PREV_TAG ==="

export IMAGE_TAG="$PREV_TAG"

docker compose \
  -f "$REPO_ROOT/docker-compose.yml" \
  -f "$REPO_ROOT/docker-compose.prod.yml" \
  pull backend nginx

docker compose \
  -f "$REPO_ROOT/docker-compose.yml" \
  -f "$REPO_ROOT/docker-compose.prod.yml" \
  up -d --no-build

bash "$SCRIPT_DIR/health-check.sh"

echo "=== Rollback complete: $PREV_TAG ==="
echo "NOTE: If migration rollback is needed, run manually:"
echo "  docker compose run --rm backend python manage.py migrate <app> <migration>"
