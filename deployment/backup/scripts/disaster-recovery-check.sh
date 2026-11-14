#!/usr/bin/env bash
# =============================================================================
# RestaurantFlow — Disaster Recovery Health Check
# Phase 25
#
# Checks:
#   1. PostgreSQL connectivity (pg_isready)
#   2. Redis connectivity (redis-cli ping)
#   3. Disk space on backup volume
#   4. Age of last backup file in BACKUP_LOCAL_DIR
#
# Exits 0 if all checks pass, 1 if any check fails.
# Prints a summary suitable for monitoring dashboards.
#
# Required environment variables:
#   DB_HOST, DB_PORT, DB_USER, BACKUP_LOCAL_DIR
# Optional:
#   REDIS_HOST (default: localhost), REDIS_PORT (default: 6379)
#   REDIS_PASSWORD, BACKUP_MAX_AGE_HOURS (default: 25)
#   BACKUP_DISK_MIN_GB (default: 5)
# =============================================================================

set -euo pipefail

: "${DB_HOST:?DB_HOST must be set}"
: "${DB_PORT:?DB_PORT must be set}"
: "${DB_USER:?DB_USER must be set}"
: "${BACKUP_LOCAL_DIR:?BACKUP_LOCAL_DIR must be set}"

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-25}"
BACKUP_DISK_MIN_GB="${BACKUP_DISK_MIN_GB:-5}"

PASS=0
FAIL=0

check_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
check_fail() { echo "  [FAIL] $1" >&2; FAIL=$((FAIL + 1)); }

echo "=============================="
echo "RestaurantFlow DR Health Check"
echo "=============================="

# ---------------------------------------------------------------------------
# 1. PostgreSQL connectivity
# ---------------------------------------------------------------------------
echo ""
echo "[1] PostgreSQL connectivity"
if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -q 2>/dev/null; then
    check_pass "PostgreSQL is accepting connections at ${DB_HOST}:${DB_PORT}"
else
    check_fail "PostgreSQL NOT ready at ${DB_HOST}:${DB_PORT}"
fi

# ---------------------------------------------------------------------------
# 2. Redis connectivity
# ---------------------------------------------------------------------------
echo ""
echo "[2] Redis connectivity"
REDIS_PING_ARGS=(-h "${REDIS_HOST}" -p "${REDIS_PORT}")
if [ -n "${REDIS_PASSWORD:-}" ]; then
    REDIS_PING_ARGS+=(-a "${REDIS_PASSWORD}")
fi
if redis-cli "${REDIS_PING_ARGS[@]}" ping 2>/dev/null | grep -q "PONG"; then
    check_pass "Redis is responding at ${REDIS_HOST}:${REDIS_PORT}"
else
    check_fail "Redis NOT responding at ${REDIS_HOST}:${REDIS_PORT}"
fi

# ---------------------------------------------------------------------------
# 3. Disk space on backup volume
# ---------------------------------------------------------------------------
echo ""
echo "[3] Backup disk space"
if [ -d "${BACKUP_LOCAL_DIR}" ]; then
    AVAIL_KB=$(df -k "${BACKUP_LOCAL_DIR}" | awk 'NR==2{print $4}')
    AVAIL_GB=$(echo "scale=1; ${AVAIL_KB} / 1048576" | bc 2>/dev/null || echo "unknown")
    if [ "${AVAIL_KB}" -gt "$((BACKUP_DISK_MIN_GB * 1048576))" ]; then
        check_pass "Backup volume has ${AVAIL_GB}GB available (min: ${BACKUP_DISK_MIN_GB}GB)"
    else
        check_fail "Low disk space on backup volume: ${AVAIL_GB}GB (min: ${BACKUP_DISK_MIN_GB}GB)"
    fi
else
    check_fail "BACKUP_LOCAL_DIR does not exist: ${BACKUP_LOCAL_DIR}"
fi

# ---------------------------------------------------------------------------
# 4. Age of most recent backup file
# ---------------------------------------------------------------------------
echo ""
echo "[4] Backup freshness"
LATEST_BACKUP=$(find "${BACKUP_LOCAL_DIR}" -maxdepth 1 -type f \
    \( -name "db_*.pgdump.gz" -o -name "db_*.pgdump.gz.gpg" \) \
    2>/dev/null | sort | tail -1)

if [ -z "${LATEST_BACKUP}" ]; then
    check_fail "No database backup files found in ${BACKUP_LOCAL_DIR}"
else
    FILE_AGE_SECONDS=$(( $(date +%s) - $(stat -c%Y "${LATEST_BACKUP}" 2>/dev/null || stat -f%m "${LATEST_BACKUP}") ))
    FILE_AGE_HOURS=$(( FILE_AGE_SECONDS / 3600 ))
    if [ "${FILE_AGE_HOURS}" -lt "${BACKUP_MAX_AGE_HOURS}" ]; then
        check_pass "Most recent backup is ${FILE_AGE_HOURS}h old (max: ${BACKUP_MAX_AGE_HOURS}h): $(basename "${LATEST_BACKUP}")"
    else
        check_fail "Most recent backup is ${FILE_AGE_HOURS}h old (max: ${BACKUP_MAX_AGE_HOURS}h): $(basename "${LATEST_BACKUP}")"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=============================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=============================="

if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
exit 0
