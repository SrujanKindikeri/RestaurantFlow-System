#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — health-check.sh
# Phase 23: Poll /health/ready/ until it returns 200 or timeout is reached.
# Usage: bash deployment/scripts/health-check.sh
# =============================================================================
set -euo pipefail

HOST="${HEALTH_CHECK_HOST:-localhost}"
PORT="${HEALTH_CHECK_PORT:-80}"
URL="http://$HOST:$PORT/health/ready/"
MAX_WAIT=120
INTERVAL=5
ELAPSED=0

echo "Waiting for $URL to become ready..."

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "Health check passed (HTTP $STATUS)"
        exit 0
    fi
    echo "Health check: HTTP $STATUS — retrying in ${INTERVAL}s (${ELAPSED}s elapsed)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo "ERROR: Health check timed out after ${MAX_WAIT}s"
exit 1
