# =============================================================================
# RestaurantFlow — Media Files Restore Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param(
    [switch]$Confirm
)

$ErrorActionPreference = 'Stop'

if (-not $Confirm) {
    Write-Error "--Confirm switch is required to perform a media restore."
    exit 1
}

$BACKUP_FILE       = [System.Environment]::GetEnvironmentVariable('BACKUP_FILE')
$RESTORE_TARGET_DIR = [System.Environment]::GetEnvironmentVariable('RESTORE_TARGET_DIR')

if ([string]::IsNullOrEmpty($BACKUP_FILE))        { throw "BACKUP_FILE env var must be set." }
if ([string]::IsNullOrEmpty($RESTORE_TARGET_DIR)) { throw "RESTORE_TARGET_DIR env var must be set." }
if (-not (Test-Path $BACKUP_FILE))                { throw "Backup file not found: $BACKUP_FILE" }

New-Item -ItemType Directory -Force -Path $RESTORE_TARGET_DIR | Out-Null

Write-Host "Starting media restore: FILE=$BACKUP_FILE TARGET=$RESTORE_TARGET_DIR"

if ($BACKUP_FILE -match '\.tar\.gz$') {
    if (Get-Command tar -ErrorAction SilentlyContinue) {
        & tar -xzf $BACKUP_FILE -C $RESTORE_TARGET_DIR
        if ($LASTEXITCODE -ne 0) { throw "tar extraction failed" }
    } else {
        throw "tar is required to extract .tar.gz archives. Install Git for Windows or WSL."
    }
} elseif ($BACKUP_FILE -match '\.zip$') {
    Expand-Archive -Path $BACKUP_FILE -DestinationPath $RESTORE_TARGET_DIR -Force
} else {
    throw "Unsupported archive format: $BACKUP_FILE"
}

Write-Host "Media restore completed: TARGET=$RESTORE_TARGET_DIR"
Write-Host "IMPORTANT: Verify file count and permissions before serving media."
