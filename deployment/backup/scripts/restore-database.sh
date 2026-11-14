#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Database Restore Script
# Phase 25
#
# Restores a pg_dump to a target database.
#
# SAFETY RULES:
#   - Requires explicit --confirm flag; without it exits 1.
#   - Never restores to the production database unless RESTORE_ALLOW_PRODUCTION=true
#     is explicitly set.
#   - Logs all steps (without emitting credentials).
#
# Required environment variables:
#   BACKUP_FILE, RESTORE_TARGET_DB, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
# Optional:
#   BACKUP_ENCRYPTION_KEY  — required for encrypted backups
#   RESTORE_ALLOW_PRODUCTION=true  — required to restore to production DB
#   DB_NAME  — name of production DB (to compare with RESTORE_TARGET_DB)
# =============================================================================

set -euo pipefail

CONFIRM=false
for arg in "$@"; do
    [ "${arg}" = "--confirm" ] && CONFIRM=true
done

if [ "${CONFIRM}" != "true" ]; then
    echo "ERROR: --confirm flag is required to perform a restore." >&2
    echo "Usage: $0 --confirm" >&2
    echo "REVIEW the target database before confirming!" >&2
    exit 1
fi

: "${BACKUP_FILE:?BACKUP_FILE must be set}"
: "${RESTORE_TARGET_DB:?RESTORE_TARGET_DB must be set}"
: "${DB_HOST:?DB_HOST must be set}"
: "${DB_PORT:?DB_PORT must be set}"
: "${DB_USER:?DB_USER must be set}"
: "${DB_PASSWORD:?DB_PASSWORD must be set}"

# ---------------------------------------------------------------------------
# Production safety guard
# ---------------------------------------------------------------------------
PRODUCTION_DB="${DB_NAME:-restaurantflow}"
if [ "${RESTORE_TARGET_DB}" = "${PRODUCTION_DB}" ]; then
    if [ "${RESTORE_ALLOW_PRODUCTION:-false}" != "true" ]; then
        echo "ERROR: RESTORE_TARGET_DB matches the production database '${PRODUCTION_DB}'." >&2
        echo "Set RESTORE_ALLOW_PRODUCTION=true to proceed — ONLY after taking a fresh backup." >&2
        exit 1
    fi
    echo "WARNING: Restoring to PRODUCTION database '${PRODUCTION_DB}'. Proceeding because RESTORE_ALLOW_PRODUCTION=true."
fi

echo "Starting restore: FILE=${BACKUP_FILE} TARGET_DB=${RESTORE_TARGET_DB} HOST=${DB_HOST}:${DB_PORT}"

# ---------------------------------------------------------------------------
# Decrypt if needed
# ---------------------------------------------------------------------------
WORK_FILE="${BACKUP_FILE}"
CLEANUP_FILE=""
if [[ "${BACKUP_FILE}" == *.gpg ]]; then
    if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
        echo "ERROR: BACKUP_ENCRYPTION_KEY required to restore encrypted backup" >&2
        exit 1
    fi
    DECRYPTED_TMP=$(mktemp --suffix=.pgdump.gz)
    CLEANUP_FILE="${DECRYPTED_TMP}"
    trap "rm -f ${CLEANUP_FILE}" EXIT
    echo "Decrypting backup..."
    echo "${BACKUP_ENCRYPTION_KEY}" | gpg \
        --batch \
        --passphrase-fd 0 \
        --decrypt \
        --output "${DECRYPTED_TMP}" \
        "${BACKUP_FILE}"
    WORK_FILE="${DECRYPTED_TMP}"
    echo "Decryption complete"
fi

# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
export PGPASSWORD="${DB_PASSWORD}"
pg_restore \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${RESTORE_TARGET_DB}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    "${WORK_FILE}"
unset PGPASSWORD

echo "Database restore completed successfully: TARGET=${RESTORE_TARGET_DB}"
echo "IMPORTANT: Run migrations and verify application before serving traffic."
exit 0
