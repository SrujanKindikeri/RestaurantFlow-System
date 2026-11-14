#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — deploy.sh
# Phase 23: Pull images, run migrations, restart services, verify health.
# Usage: bash deployment/scripts/deploy.sh [<image-tag>]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_TAG="${1:-latest}"

echo "=== Deploying RestaurantFlow: $IMAGE_TAG ==="

# Validate required environment variables
bash "$SCRIPT_DIR/validate-environment.sh"

# Back up the database before making changes
bash "$SCRIPT_DIR/backup-before-deploy.sh"

# Pull new images
export IMAGE_TAG
docker compose \
  -f "$REPO_ROOT/docker-compose.yml" \
  -f "$REPO_ROOT/docker-compose.prod.yml" \
  pull backend nginx

# Run migrations before restarting backend
docker compose \
  -f "$REPO_ROOT/docker-compose.yml" \
  -f "$REPO_ROOT/docker-compose.prod.yml" \
  run --rm backend python manage.py migrate --noinput

# Restart all services with the new images
docker compose \
  -f "$REPO_ROOT/docker-compose.yml" \
  -f "$REPO_ROOT/docker-compose.prod.yml" \
  up -d --no-build

# Verify the deployment succeeded
bash "$SCRIPT_DIR/health-check.sh"

echo "=== Deployment complete: $IMAGE_TAG ==="
