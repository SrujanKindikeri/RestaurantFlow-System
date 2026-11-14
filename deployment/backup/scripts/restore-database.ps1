# =============================================================================
# RestaurantFlow — Database Restore Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param(
    [switch]$Confirm
)

$ErrorActionPreference = 'Stop'

if (-not $Confirm) {
    Write-Error "--Confirm switch is required to perform a restore. Review target DB first."
    exit 1
}

function Require-Env {
    param([string]$Name)
    $val = [System.Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($val)) { throw "Required env var $Name is not set." }
    return $val
}

$BACKUP_FILE              = Require-Env 'BACKUP_FILE'
$RESTORE_TARGET_DB        = Require-Env 'RESTORE_TARGET_DB'
$DB_HOST                  = Require-Env 'DB_HOST'
$DB_PORT                  = Require-Env 'DB_PORT'
$DB_USER                  = Require-Env 'DB_USER'
$DB_PASSWORD              = Require-Env 'DB_PASSWORD'
$PRODUCTION_DB            = [System.Environment]::GetEnvironmentVariable('DB_NAME')
$RESTORE_ALLOW_PRODUCTION = [System.Environment]::GetEnvironmentVariable('RESTORE_ALLOW_PRODUCTION')
$BACKUP_ENCRYPTION_KEY    = [System.Environment]::GetEnvironmentVariable('BACKUP_ENCRYPTION_KEY')

if (-not [string]::IsNullOrEmpty($PRODUCTION_DB) -and $RESTORE_TARGET_DB -eq $PRODUCTION_DB) {
    if ($RESTORE_ALLOW_PRODUCTION -ne 'true') {
        throw "RESTORE_TARGET_DB matches production DB '$PRODUCTION_DB'. Set RESTORE_ALLOW_PRODUCTION=true to proceed."
    }
    Write-Host "WARNING: Restoring to PRODUCTION database."
}

Write-Host "Starting restore: FILE=$BACKUP_FILE TARGET_DB=$RESTORE_TARGET_DB HOST=${DB_HOST}:${DB_PORT}"

$WorkFile    = $BACKUP_FILE
$CleanupFile = $null

if ($BACKUP_FILE -match '\.gpg$') {
    if ([string]::IsNullOrEmpty($BACKUP_ENCRYPTION_KEY)) {
        throw "BACKUP_ENCRYPTION_KEY required to restore encrypted backup."
    }
    $Decrypted = [System.IO.Path]::GetTempFileName() + '.pgdump.gz'
    $CleanupFile = $Decrypted
    $BACKUP_ENCRYPTION_KEY | gpg --batch --passphrase-fd 0 --decrypt --output $Decrypted $BACKUP_FILE
    $WorkFile = $Decrypted
    Write-Host "Decryption complete"
}

try {
    $env:PGPASSWORD = $DB_PASSWORD
    & pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $RESTORE_TARGET_DB `
        --clean --if-exists --no-owner --no-acl $WorkFile
    if ($LASTEXITCODE -ne 0) { throw "pg_restore failed with exit code $LASTEXITCODE" }
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    if ($CleanupFile -and (Test-Path $CleanupFile)) { Remove-Item $CleanupFile -Force }
}

Write-Host "Database restore completed: TARGET=$RESTORE_TARGET_DB"
Write-Host "IMPORTANT: Run migrations and verify application before serving traffic."
