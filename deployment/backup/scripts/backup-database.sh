#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Database Backup Script
# Phase 25
#
# Creates a pg_dump, gzip-compresses, optionally encrypts with GPG,
# writes a SHA-256 sidecar file, and optionally uploads to S3.
#
# Required environment variables:
#   DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, BACKUP_LOCAL_DIR
# Optional:
#   BACKUP_ENCRYPTION_KEY  — if set, backup is encrypted with GPG
#   BACKUP_S3_BUCKET       — if set, upload to S3
#   BACKUP_S3_PREFIX       — S3 key prefix (default: db-backups)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Validate required environment variables
# ---------------------------------------------------------------------------
: "${DB_HOST:?DB_HOST must be set}"
: "${DB_PORT:?DB_PORT must be set}"
: "${DB_NAME:?DB_NAME must be set}"
: "${DB_USER:?DB_USER must be set}"
: "${DB_PASSWORD:?DB_PASSWORD must be set}"
: "${BACKUP_LOCAL_DIR:?BACKUP_LOCAL_DIR must be set}"

mkdir -p "${BACKUP_LOCAL_DIR}"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BASE_NAME="db_${DB_NAME}_${TIMESTAMP}"
DUMP_FILE="${BACKUP_LOCAL_DIR}/${BASE_NAME}.pgdump.gz"

if [ -n "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    FINAL_FILE="${DUMP_FILE}.gpg"
else
    FINAL_FILE="${DUMP_FILE}"
fi
CHECKSUM_FILE="${FINAL_FILE}.sha256"

# Never overwrite an existing backup
if [ -f "${FINAL_FILE}" ]; then
    echo "ERROR: backup file already exists: ${FINAL_FILE}" >&2
    exit 1
fi

echo "Starting database backup: DB=${DB_NAME} HOST=${DB_HOST}:${DB_PORT}"

# ---------------------------------------------------------------------------
# Run pg_dump via PGPASSWORD env var (never pass -W flag with password)
# ---------------------------------------------------------------------------
export PGPASSWORD="${DB_PASSWORD}"
pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -Fc \
    "${DB_NAME}" \
    | gzip -6 > "${DUMP_FILE}"
unset PGPASSWORD

echo "pg_dump completed: ${DUMP_FILE}"

# ---------------------------------------------------------------------------
# Encrypt if key is provided
# ---------------------------------------------------------------------------
if [ -n "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    echo "${BACKUP_ENCRYPTION_KEY}" | gpg \
        --batch \
        --yes \
        --passphrase-fd 0 \
        --symmetric \
        --cipher-algo AES256 \
        --output "${FINAL_FILE}" \
        "${DUMP_FILE}"
    rm -f "${DUMP_FILE}"
    echo "Encryption complete: ${FINAL_FILE}"
fi

# ---------------------------------------------------------------------------
# Verify output is non-empty
# ---------------------------------------------------------------------------
if [ ! -s "${FINAL_FILE}" ]; then
    echo "ERROR: backup file is empty: ${FINAL_FILE}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Compute and write SHA-256 checksum
# ---------------------------------------------------------------------------
sha256sum "${FINAL_FILE}" | awk '{print $1}' > "${CHECKSUM_FILE}"
echo "Checksum: $(cat "${CHECKSUM_FILE}")"

# ---------------------------------------------------------------------------
# Optional S3 upload
# ---------------------------------------------------------------------------
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    PREFIX="${BACKUP_S3_PREFIX:-db-backups}"
    S3_KEY="${PREFIX}/$(basename "${FINAL_FILE}")"
    echo "Uploading to s3://${BACKUP_S3_BUCKET}/${S3_KEY}"
    aws s3 cp "${FINAL_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" \
        --no-progress \
        --storage-class STANDARD_IA
    aws s3 cp "${CHECKSUM_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}.sha256" \
        --no-progress
    echo "S3 upload complete"
fi

# Output file path for the calling process (Celery task parses this)
echo "BACKUP_FILE=${FINAL_FILE}"

echo "Database backup finished successfully: ${FINAL_FILE}"
exit 0
