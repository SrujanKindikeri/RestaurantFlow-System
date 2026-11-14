# =============================================================================
# RestaurantFlow — Backup Retention Cleanup Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'

if (-not $Execute -and -not $DryRun) {
    # Default to dry-run
    $DryRun = $true
}

$BACKUP_LOCAL_DIR    = [System.Environment]::GetEnvironmentVariable('BACKUP_LOCAL_DIR')
$BACKUP_RETENTION_DAYS = [System.Environment]::GetEnvironmentVariable('BACKUP_RETENTION_DAYS')

if ([string]::IsNullOrEmpty($BACKUP_LOCAL_DIR))    { throw "BACKUP_LOCAL_DIR must be set." }
if ([string]::IsNullOrEmpty($BACKUP_RETENTION_DAYS)) { throw "BACKUP_RETENTION_DAYS must be set." }

$RetentionDays = [int]$BACKUP_RETENTION_DAYS
$Cutoff        = (Get-Date).AddDays(-$RetentionDays)

if ($DryRun) {
    Write-Host "DRY-RUN mode: no files will be deleted. Pass -Execute to delete."
}

Write-Host "Scanning: $BACKUP_LOCAL_DIR (retention: $RetentionDays days)"

$Patterns  = @('db_*.pgdump.gz', 'db_*.pgdump.gz.gpg', 'media_*.tar.gz', 'config_*.zip', 'redis_aof_*.aof')
$Candidates = @()
foreach ($Pattern in $Patterns) {
    $Candidates += Get-ChildItem -Path $BACKUP_LOCAL_DIR -Filter $Pattern -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $Cutoff }
}
$Candidates = $Candidates | Sort-Object FullName

# Identify the most recent file of each type to protect
$LatestDb     = Get-ChildItem -Path $BACKUP_LOCAL_DIR -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^db_' } | Sort-Object FullName | Select-Object -Last 1
$LatestMedia  = Get-ChildItem -Path $BACKUP_LOCAL_DIR -Filter 'media_*.tar.gz' -File -ErrorAction SilentlyContinue |
    Sort-Object FullName | Select-Object -Last 1
$LatestConfig = Get-ChildItem -Path $BACKUP_LOCAL_DIR -Filter 'config_*.zip' -File -ErrorAction SilentlyContinue |
    Sort-Object FullName | Select-Object -Last 1

$Protected = @($LatestDb?.FullName, $LatestMedia?.FullName, $LatestConfig?.FullName) | Where-Object { $_ }

$Deleted = 0
foreach ($File in $Candidates) {
    if ($Protected -contains $File.FullName) {
        Write-Host "PROTECTED (last of type): $($File.Name)"
        continue
    }
    if ($Execute) {
        Remove-Item $File.FullName -Force -ErrorAction SilentlyContinue
        Remove-Item "$($File.FullName).sha256" -Force -ErrorAction SilentlyContinue
        Write-Host "DELETED: $($File.Name)"
    } else {
        Write-Host "WOULD DELETE: $($File.Name)"
    }
    $Deleted++
}

$Action = if ($Execute) { "deleted" } else { "would be deleted" }
Write-Host "Cleanup complete: $Deleted files $Action."
