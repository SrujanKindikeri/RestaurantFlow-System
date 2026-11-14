#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Configuration Backup Script
# Phase 25
#
# Archives non-secret configuration files. Explicitly EXCLUDES .env files
# and any file containing passwords/secrets.
#
# Required environment variables:
#   BACKUP_LOCAL_DIR
# Optional:
#   BACKUP_REDIS_AOF=true  — also backs up Redis AOF file
#   REDIS_AOF_DIR          — directory containing appendonly.aof (default /data)
#   BACKUP_S3_BUCKET, BACKUP_S3_PREFIX
# =============================================================================

set -euo pipefail

: "${BACKUP_LOCAL_DIR:?BACKUP_LOCAL_DIR must be set}"

mkdir -p "${BACKUP_LOCAL_DIR}"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE="${BACKUP_LOCAL_DIR}/config_${TIMESTAMP}.tar.gz"
CHECKSUM_FILE="${ARCHIVE}.sha256"

if [ -f "${ARCHIVE}" ]; then
    echo "ERROR: backup file already exists: ${ARCHIVE}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Build list of safe config files to archive
# Never include .env, *.pem, *.key, or files likely to contain credentials
# ---------------------------------------------------------------------------
TMPLIST=$(mktemp)
trap "rm -f ${TMPLIST}" EXIT

# From the project root (two levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

{
    # docker-compose files (no secrets — credentials come from env)
    find "${PROJECT_ROOT}" -maxdepth 1 -name "docker-compose*.yml" -not -name "*.secret*"
    # nginx configuration (if present)
    find "${PROJECT_ROOT}/deployment/nginx" -name "*.conf" 2>/dev/null || true
    # deployment scripts (bash/ps1) but NOT environment files
    find "${PROJECT_ROOT}/deployment" -name "*.sh" -o -name "*.ps1" 2>/dev/null | grep -v ".env" || true
    # This backup scripts directory
    find "${SCRIPT_DIR}" -type f 2>/dev/null || true
} | sort -u > "${TMPLIST}"

echo "Files to archive:"
cat "${TMPLIST}"

tar -czf "${ARCHIVE}" -T "${TMPLIST}" --transform "s|${PROJECT_ROOT}/||"

if [ ! -s "${ARCHIVE}" ]; then
    echo "ERROR: configuration archive is empty" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Optional Redis AOF backup
# ---------------------------------------------------------------------------
if [ "${BACKUP_REDIS_AOF:-false}" = "true" ]; then
    AOF_DIR="${REDIS_AOF_DIR:-/data}"
    AOF_FILE="${AOF_DIR}/appendonly.aof"
    if [ -f "${AOF_FILE}" ]; then
        AOF_BACKUP="${BACKUP_LOCAL_DIR}/redis_aof_${TIMESTAMP}.aof"
        cp "${AOF_FILE}" "${AOF_BACKUP}"
        sha256sum "${AOF_BACKUP}" | awk '{print $1}' > "${AOF_BACKUP}.sha256"
        echo "Redis AOF backed up: ${AOF_BACKUP}"
    else
        echo "WARNING: BACKUP_REDIS_AOF=true but ${AOF_FILE} not found" >&2
    fi
fi

sha256sum "${ARCHIVE}" | awk '{print $1}' > "${CHECKSUM_FILE}"
echo "Checksum: $(cat "${CHECKSUM_FILE}")"

if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    PREFIX="${BACKUP_S3_PREFIX:-config-backups}"
    S3_KEY="${PREFIX}/$(basename "${ARCHIVE}")"
    aws s3 cp "${ARCHIVE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" --no-progress
    aws s3 cp "${CHECKSUM_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}.sha256" --no-progress
    echo "S3 upload complete"
fi

echo "BACKUP_FILE=${ARCHIVE}"
echo "Configuration backup finished successfully"
exit 0
