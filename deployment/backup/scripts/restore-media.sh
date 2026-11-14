#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Media Files Restore Script
# Phase 25
#
# Restores a media archive to RESTORE_TARGET_DIR.
# Requires --confirm flag; default is dry-run (shows what would be extracted).
#
# Required environment variables:
#   BACKUP_FILE, RESTORE_TARGET_DIR
# =============================================================================

set -euo pipefail

CONFIRM=false
for arg in "$@"; do
    [ "${arg}" = "--confirm" ] && CONFIRM=true
done

if [ "${CONFIRM}" != "true" ]; then
    echo "ERROR: --confirm flag is required to perform a media restore." >&2
    echo "Usage: $0 --confirm" >&2
    exit 1
fi

: "${BACKUP_FILE:?BACKUP_FILE must be set}"
: "${RESTORE_TARGET_DIR:?RESTORE_TARGET_DIR must be set}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

mkdir -p "${RESTORE_TARGET_DIR}"

echo "Starting media restore: FILE=${BACKUP_FILE} TARGET=${RESTORE_TARGET_DIR}"

tar -xzf "${BACKUP_FILE}" -C "${RESTORE_TARGET_DIR}"

echo "Media restore completed successfully: TARGET=${RESTORE_TARGET_DIR}"
echo "IMPORTANT: Verify file count and permissions before serving media."
exit 0
