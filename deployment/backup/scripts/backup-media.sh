#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Media Files Backup Script
# Phase 25
#
# Archives the media directory, writes a SHA-256 sidecar, optionally uploads
# to S3.
#
# Required environment variables:
#   MEDIA_DIR, BACKUP_LOCAL_DIR
# Optional:
#   BACKUP_S3_BUCKET, BACKUP_S3_PREFIX
# =============================================================================

set -euo pipefail

: "${MEDIA_DIR:?MEDIA_DIR must be set}"
: "${BACKUP_LOCAL_DIR:?BACKUP_LOCAL_DIR must be set}"

if [ ! -d "${MEDIA_DIR}" ]; then
    echo "ERROR: MEDIA_DIR does not exist: ${MEDIA_DIR}" >&2
    exit 1
fi

mkdir -p "${BACKUP_LOCAL_DIR}"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE="${BACKUP_LOCAL_DIR}/media_${TIMESTAMP}.tar.gz"
CHECKSUM_FILE="${ARCHIVE}.sha256"

if [ -f "${ARCHIVE}" ]; then
    echo "ERROR: backup file already exists: ${ARCHIVE}" >&2
    exit 1
fi

echo "Starting media backup: MEDIA_DIR=${MEDIA_DIR}"

tar -czf "${ARCHIVE}" -C "$(dirname "${MEDIA_DIR}")" "$(basename "${MEDIA_DIR}")"

if [ ! -s "${ARCHIVE}" ]; then
    echo "ERROR: media archive is empty: ${ARCHIVE}" >&2
    exit 1
fi

sha256sum "${ARCHIVE}" | awk '{print $1}' > "${CHECKSUM_FILE}"
echo "Checksum: $(cat "${CHECKSUM_FILE}")"

if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    PREFIX="${BACKUP_S3_PREFIX:-media-backups}"
    S3_KEY="${PREFIX}/$(basename "${ARCHIVE}")"
    echo "Uploading to s3://${BACKUP_S3_BUCKET}/${S3_KEY}"
    aws s3 cp "${ARCHIVE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" --no-progress --storage-class STANDARD_IA
    aws s3 cp "${CHECKSUM_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}.sha256" --no-progress
    echo "S3 upload complete"
fi

echo "BACKUP_FILE=${ARCHIVE}"
echo "Media backup finished successfully: ${ARCHIVE}"
exit 0
