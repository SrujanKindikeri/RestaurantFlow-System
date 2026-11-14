#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Backup Verification Script
# Phase 25
#
# Verifies a backup file by:
#   1. Checking the file exists and is non-empty
#   2. Computing SHA-256 and comparing against .sha256 sidecar
#   3. For .pgdump files: decrypting and running pg_restore --list
#
# Required environment variables:
#   BACKUP_FILE — full path to the backup file
# Optional:
#   BACKUP_ENCRYPTION_KEY — required to decrypt .gpg files
# =============================================================================

set -euo pipefail

: "${BACKUP_FILE:?BACKUP_FILE must be set}"

CHECKSUM_FILE="${BACKUP_FILE}.sha256"

echo "Verifying backup: ${BACKUP_FILE}"

# ---------------------------------------------------------------------------
# 1. File exists and is non-empty
# ---------------------------------------------------------------------------
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

if [ ! -s "${BACKUP_FILE}" ]; then
    echo "ERROR: backup file is empty: ${BACKUP_FILE}" >&2
    exit 1
fi

FILE_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}")
echo "File size: ${FILE_SIZE} bytes"

# ---------------------------------------------------------------------------
# 2. SHA-256 checksum verification
# ---------------------------------------------------------------------------
if [ ! -f "${CHECKSUM_FILE}" ]; then
    echo "ERROR: checksum file not found: ${CHECKSUM_FILE}" >&2
    exit 1
fi

EXPECTED_CHECKSUM=$(cat "${CHECKSUM_FILE}")
ACTUAL_CHECKSUM=$(sha256sum "${BACKUP_FILE}" | awk '{print $1}')

if [ "${EXPECTED_CHECKSUM}" != "${ACTUAL_CHECKSUM}" ]; then
    echo "ERROR: checksum mismatch!" >&2
    echo "  Expected: ${EXPECTED_CHECKSUM}" >&2
    echo "  Actual:   ${ACTUAL_CHECKSUM}" >&2
    exit 1
fi

echo "Checksum verified: ${ACTUAL_CHECKSUM}"

# ---------------------------------------------------------------------------
# 3. Structural verification for .pgdump files
# ---------------------------------------------------------------------------
if [[ "${BACKUP_FILE}" == *.pgdump* ]]; then
    if [[ "${BACKUP_FILE}" == *.gpg ]]; then
        # Need to decrypt first
        if [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
            echo "ERROR: BACKUP_ENCRYPTION_KEY required to verify encrypted dump" >&2
            exit 1
        fi
        DECRYPTED_TMP=$(mktemp --suffix=.pgdump.gz)
        trap "rm -f ${DECRYPTED_TMP}" EXIT
        echo "${BACKUP_ENCRYPTION_KEY}" | gpg \
            --batch \
            --passphrase-fd 0 \
            --decrypt \
            --output "${DECRYPTED_TMP}" \
            "${BACKUP_FILE}"
        pg_restore --list "${DECRYPTED_TMP}" > /dev/null
        echo "pg_restore structure check passed on decrypted dump"
    else
        pg_restore --list "${BACKUP_FILE}" > /dev/null
        echo "pg_restore structure check passed"
    fi
fi

echo "Backup verification PASSED: ${BACKUP_FILE}"
exit 0
