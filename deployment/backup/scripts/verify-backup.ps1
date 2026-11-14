# =============================================================================
# RestaurantFlow — Backup Verification Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$BACKUP_FILE = [System.Environment]::GetEnvironmentVariable('BACKUP_FILE')
if ([string]::IsNullOrEmpty($BACKUP_FILE)) { throw "BACKUP_FILE environment variable must be set." }

$ChecksumFile = "${BACKUP_FILE}.sha256"

Write-Host "Verifying backup: $BACKUP_FILE"

# 1. File exists and is non-empty
if (-not (Test-Path $BACKUP_FILE)) { throw "Backup file not found: $BACKUP_FILE" }
$FileInfo = Get-Item $BACKUP_FILE
if ($FileInfo.Length -eq 0) { throw "Backup file is empty: $BACKUP_FILE" }
Write-Host "File size: $($FileInfo.Length) bytes"

# 2. Checksum verification
if (-not (Test-Path $ChecksumFile)) { throw "Checksum file not found: $ChecksumFile" }
$Expected = (Get-Content $ChecksumFile -Raw).Trim().ToLower()
$Actual   = (Get-FileHash -Algorithm SHA256 $BACKUP_FILE).Hash.ToLower()

if ($Expected -ne $Actual) {
    throw "Checksum mismatch! Expected: $Expected  Actual: $Actual"
}
Write-Host "Checksum verified: $Actual"

# 3. Structural check for pgdump files (requires pg_restore in PATH)
if ($BACKUP_FILE -match '\.pgdump') {
    if (Get-Command pg_restore -ErrorAction SilentlyContinue) {
        & pg_restore --list $BACKUP_FILE > $null
        if ($LASTEXITCODE -ne 0) { throw "pg_restore --list failed on: $BACKUP_FILE" }
        Write-Host "pg_restore structure check passed"
    } else {
        Write-Host "WARNING: pg_restore not in PATH — skipping structural check"
    }
}

Write-Host "Backup verification PASSED: $BACKUP_FILE"
