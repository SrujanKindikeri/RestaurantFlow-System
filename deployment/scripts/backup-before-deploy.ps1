# =============================================================================
# RestaurantFlow — backup-before-deploy.ps1
# Phase 23: Dump a Postgres snapshot before deploying (Windows).
# Usage: .\deployment\scripts\backup-before-deploy.ps1
# =============================================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path "$ScriptDir\..\.."
$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { "$RepoRoot\backups" }

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$File      = "$BackupDir\pre_deploy_$Timestamp.sql"
$DbUser    = if ($env:DB_USER) { $env:DB_USER } else { "restaurantflow" }
$DbName    = if ($env:DB_NAME) { $env:DB_NAME } else { "restaurantflow" }

Write-Host "Creating database backup: $File"

docker compose `
    -f "$RepoRoot\docker-compose.yml" `
    -f "$RepoRoot\docker-compose.prod.yml" `
    exec -T postgres pg_dump -U $DbUser -d $DbName `
    | Out-File -FilePath $File -Encoding utf8

Write-Host "Backup complete: $File"

# Retain only the 7 most recent backups
$backups = Get-ChildItem "$BackupDir\pre_deploy_*.sql" | Sort-Object LastWriteTime -Descending
if ($backups.Count -gt 7) {
    $backups | Select-Object -Skip 7 | Remove-Item
}

Write-Host "Old backups pruned (keeping 7 most recent)"
