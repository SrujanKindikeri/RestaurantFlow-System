#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — build.sh
# Phase 23: Build backend and frontend Docker images.
# Usage: bash deployment/scripts/build.sh [<image-tag>]
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_TAG="${1:-$(git -C "$REPO_ROOT" rev-parse --short HEAD)}"
GHCR_OWNER="${GHCR_OWNER:-restaurantflow}"

echo "Building images with tag: $IMAGE_TAG"

docker build \
  -t "ghcr.io/$GHCR_OWNER/restaurantflow-backend:$IMAGE_TAG" \
  "$REPO_ROOT/backend"

docker build \
  --build-arg VITE_API_URL="${VITE_API_URL:-https://yourdomain.com/api}" \
  --build-arg VITE_WS_URL="${VITE_WS_URL:-wss://yourdomain.com}" \
  --build-arg VITE_APP_NAME="RestaurantFlow" \
  -t "ghcr.io/$GHCR_OWNER/restaurantflow-frontend:$IMAGE_TAG" \
  "$REPO_ROOT/frontend"

echo "Build complete: $IMAGE_TAG"
