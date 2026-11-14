# =============================================================================
# RestaurantFlow — Database Backup Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Validate required environment variables
# ---------------------------------------------------------------------------
function Require-Env {
    param([string]$Name)
    $val = [System.Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($val)) {
        throw "Required environment variable $Name is not set."
    }
    return $val
}

$DB_HOST          = Require-Env 'DB_HOST'
$DB_PORT          = Require-Env 'DB_PORT'
$DB_NAME          = Require-Env 'DB_NAME'
$DB_USER          = Require-Env 'DB_USER'
$DB_PASSWORD      = Require-Env 'DB_PASSWORD'
$BACKUP_LOCAL_DIR = Require-Env 'BACKUP_LOCAL_DIR'

$BACKUP_ENCRYPTION_KEY = [System.Environment]::GetEnvironmentVariable('BACKUP_ENCRYPTION_KEY')
$BACKUP_S3_BUCKET      = [System.Environment]::GetEnvironmentVariable('BACKUP_S3_BUCKET')
$BACKUP_S3_PREFIX      = [System.Environment]::GetEnvironmentVariable('BACKUP_S3_PREFIX')
if ([string]::IsNullOrEmpty($BACKUP_S3_PREFIX)) { $BACKUP_S3_PREFIX = 'db-backups' }

New-Item -ItemType Directory -Force -Path $BACKUP_LOCAL_DIR | Out-Null

$Timestamp = (Get-Date -Format 'yyyyMMddTHHmmssZ')
$BaseName  = "db_${DB_NAME}_${Timestamp}"
$DumpFile  = Join-Path $BACKUP_LOCAL_DIR "${BaseName}.pgdump.gz"

if (-not [string]::IsNullOrEmpty($BACKUP_ENCRYPTION_KEY)) {
    $FinalFile = "${DumpFile}.gpg"
} else {
    $FinalFile = $DumpFile
}
$ChecksumFile = "${FinalFile}.sha256"

if (Test-Path $FinalFile) {
    throw "Backup file already exists: $FinalFile"
}

Write-Host "Starting database backup: DB=$DB_NAME HOST=${DB_HOST}:${DB_PORT}"

# ---------------------------------------------------------------------------
# Run pg_dump — set PGPASSWORD in environment, never in args
# ---------------------------------------------------------------------------
$env:PGPASSWORD = $DB_PASSWORD
try {
    $pgArgs = @('-h', $DB_HOST, '-p', $DB_PORT, '-U', $DB_USER, '-Fc', $DB_NAME)
    $dumpOutput = & pg_dump @pgArgs
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }
    # Compress
    $dumpOutput | gzip | Set-Content -Path $DumpFile -AsByteStream
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "pg_dump completed: $DumpFile"

# ---------------------------------------------------------------------------
# Encrypt if key provided (requires gpg in PATH)
# ---------------------------------------------------------------------------
if (-not [string]::IsNullOrEmpty($BACKUP_ENCRYPTION_KEY)) {
    $BACKUP_ENCRYPTION_KEY | gpg --batch --yes --passphrase-fd 0 `
        --symmetric --cipher-algo AES256 --output $FinalFile $DumpFile
    if ($LASTEXITCODE -ne 0) { throw "GPG encryption failed" }
    Remove-Item $DumpFile -Force
    Write-Host "Encryption complete: $FinalFile"
}

if (-not (Test-Path $FinalFile) -or (Get-Item $FinalFile).Length -eq 0) {
    throw "Backup file is empty or missing: $FinalFile"
}

# ---------------------------------------------------------------------------
# SHA-256 checksum
# ---------------------------------------------------------------------------
$Hash = (Get-FileHash -Algorithm SHA256 $FinalFile).Hash.ToLower()
Set-Content -Path $ChecksumFile -Value $Hash -NoNewline
Write-Host "Checksum: $Hash"

# ---------------------------------------------------------------------------
# Optional S3 upload
# ---------------------------------------------------------------------------
if (-not [string]::IsNullOrEmpty($BACKUP_S3_BUCKET)) {
    $S3Key = "${BACKUP_S3_PREFIX}/$(Split-Path $FinalFile -Leaf)"
    & aws s3 cp $FinalFile "s3://${BACKUP_S3_BUCKET}/${S3Key}" --no-progress --storage-class STANDARD_IA
    & aws s3 cp $ChecksumFile "s3://${BACKUP_S3_BUCKET}/${S3Key}.sha256" --no-progress
    Write-Host "S3 upload complete"
}

Write-Host "BACKUP_FILE=$FinalFile"
Write-Host "Database backup finished successfully: $FinalFile"
