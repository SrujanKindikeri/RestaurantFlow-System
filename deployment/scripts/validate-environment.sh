#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — validate-environment.sh
# Phase 23: Confirm required env vars are set before deploying.
# Usage: bash deployment/scripts/validate-environment.sh
# =============================================================================
set -euo pipefail

REQUIRED_VARS=(
    SECRET_KEY
    DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT
    REDIS_URL REDIS_PASSWORD
    ALLOWED_HOSTS CORS_ALLOWED_ORIGINS CSRF_TRUSTED_ORIGINS
)

MISSING=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR:-}" ]; then
        MISSING+=("$VAR")
    fi
done

if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "ERROR: Missing required environment variables:"
    for V in "${MISSING[@]}"; do echo "  - $V"; done
    exit 1
fi

if [ "${SECRET_KEY}" = "change-me-use-a-50-char-random-string" ] \
|| [ "${SECRET_KEY}" = "dev-only-insecure-key-DO-NOT-USE-IN-PRODUCTION" ]; then
    echo "ERROR: SECRET_KEY is set to an insecure default value."
    exit 1
fi

echo "Environment validation passed."
