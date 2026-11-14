#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Backup Retention Cleanup Script
# Phase 25
#
# Deletes backup files older than BACKUP_RETENTION_DAYS.
# Default mode is --dry-run; pass --execute to actually delete.
#
# Safety: never deletes the most recent backup file of each type.
#
# Required environment variables:
#   BACKUP_LOCAL_DIR, BACKUP_RETENTION_DAYS
# =============================================================================

set -euo pipefail

: "${BACKUP_LOCAL_DIR:?BACKUP_LOCAL_DIR must be set}"
: "${BACKUP_RETENTION_DAYS:?BACKUP_RETENTION_DAYS must be set}"

EXECUTE=false
for arg in "$@"; do
    [ "${arg}" = "--execute" ] && EXECUTE=true
done

if [ "${EXECUTE}" != "true" ]; then
    echo "DRY-RUN mode: no files will be deleted. Pass --execute to delete."
fi

echo "Scanning: ${BACKUP_LOCAL_DIR} (retention: ${BACKUP_RETENTION_DAYS} days)"

# Find files older than retention period
CANDIDATES=$(find "${BACKUP_LOCAL_DIR}" -maxdepth 1 -type f \
    \( -name "*.pgdump.gz" -o -name "*.pgdump.gz.gpg" -o -name "*.tar.gz" -o -name "*.aof" \) \
    -mtime "+${BACKUP_RETENTION_DAYS}" 2>/dev/null | sort)

if [ -z "${CANDIDATES}" ]; then
    echo "No files found older than ${BACKUP_RETENTION_DAYS} days."
    exit 0
fi

# ---------------------------------------------------------------------------
# Identify the most recent file of each type (by modification time) to protect
# ---------------------------------------------------------------------------
LATEST_DB=$(find "${BACKUP_LOCAL_DIR}" -maxdepth 1 -type f \
    \( -name "db_*.pgdump.gz" -o -name "db_*.pgdump.gz.gpg" \) \
    2>/dev/null | sort | tail -1)
LATEST_MEDIA=$(find "${BACKUP_LOCAL_DIR}" -maxdepth 1 -type f \
    -name "media_*.tar.gz" 2>/dev/null | sort | tail -1)
LATEST_CONFIG=$(find "${BACKUP_LOCAL_DIR}" -maxdepth 1 -type f \
    -name "config_*.tar.gz" 2>/dev/null | sort | tail -1)

PROTECTED="${LATEST_DB} ${LATEST_MEDIA} ${LATEST_CONFIG}"
DELETED=0

while IFS= read -r FILE; do
    BASENAME=$(basename "${FILE}")
    # Check if this file is in the protected set
    IS_PROTECTED=false
    for PROT in ${PROTECTED}; do
        if [ "${FILE}" = "${PROT}" ]; then
            IS_PROTECTED=true
            break
        fi
    done

    if [ "${IS_PROTECTED}" = "true" ]; then
        echo "PROTECTED (last backup of type): ${BASENAME}"
        continue
    fi

    if [ "${EXECUTE}" = "true" ]; then
        rm -f "${FILE}" "${FILE}.sha256" 2>/dev/null || true
        echo "DELETED: ${BASENAME}"
        DELETED=$((DELETED + 1))
    else
        echo "WOULD DELETE: ${BASENAME}"
        DELETED=$((DELETED + 1))
    fi
done <<< "${CANDIDATES}"

if [ "${EXECUTE}" = "true" ]; then
    echo "Cleanup complete: ${DELETED} files deleted."
else
    echo "Dry-run complete: ${DELETED} files would be deleted. Pass --execute to delete."
fi
exit 0
