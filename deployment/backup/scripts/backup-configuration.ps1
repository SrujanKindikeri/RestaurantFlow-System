# =============================================================================
# RestaurantFlow — Configuration Backup Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Require-Env {
    param([string]$Name)
    $val = [System.Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($val)) { throw "Required env var $Name is not set." }
    return $val
}

$BACKUP_LOCAL_DIR  = Require-Env 'BACKUP_LOCAL_DIR'
$BACKUP_S3_BUCKET  = [System.Environment]::GetEnvironmentVariable('BACKUP_S3_BUCKET')
$BACKUP_S3_PREFIX  = [System.Environment]::GetEnvironmentVariable('BACKUP_S3_PREFIX')
$BACKUP_REDIS_AOF  = [System.Environment]::GetEnvironmentVariable('BACKUP_REDIS_AOF')
$REDIS_AOF_DIR     = [System.Environment]::GetEnvironmentVariable('REDIS_AOF_DIR')
if ([string]::IsNullOrEmpty($REDIS_AOF_DIR)) { $REDIS_AOF_DIR = '/data' }

New-Item -ItemType Directory -Force -Path $BACKUP_LOCAL_DIR | Out-Null

$Timestamp    = (Get-Date -Format 'yyyyMMddTHHmmssZ')
$Archive      = Join-Path $BACKUP_LOCAL_DIR "config_${Timestamp}.zip"
$ChecksumFile = "${Archive}.sha256"

if (Test-Path $Archive) { throw "Backup file already exists: $Archive" }

# ---------------------------------------------------------------------------
# Gather non-secret config files from project root
# Explicitly EXCLUDE .env, *.pem, *.key, secrets
# ---------------------------------------------------------------------------
$ScriptDir   = Split-Path $MyInvocation.MyCommand.Path -Parent
$ProjectRoot = (Get-Item (Join-Path $ScriptDir '..\..\..') -ErrorAction SilentlyContinue)?.FullName
if (-not $ProjectRoot) { $ProjectRoot = Join-Path $ScriptDir '..\..\..'}

$FilesToArchive = @()

# docker-compose files
Get-ChildItem -Path $ProjectRoot -Filter 'docker-compose*.yml' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch '\.secret' } |
    ForEach-Object { $FilesToArchive += $_.FullName }

# Deployment scripts (.sh, .ps1) — exclude .env
Get-ChildItem -Path (Join-Path $ProjectRoot 'deployment') -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { ($_.Extension -in '.sh', '.ps1', '.yml', '.yaml', '.conf') -and $_.Name -notmatch '\.env' } |
    ForEach-Object { $FilesToArchive += $_.FullName }

Write-Host "Archiving $($FilesToArchive.Count) config files"

Compress-Archive -Path $FilesToArchive -DestinationPath $Archive -Force

# ---------------------------------------------------------------------------
# Optional Redis AOF backup
# ---------------------------------------------------------------------------
if ($BACKUP_REDIS_AOF -eq 'true') {
    $AofFile = Join-Path $REDIS_AOF_DIR 'appendonly.aof'
    if (Test-Path $AofFile) {
        $AofBackup = Join-Path $BACKUP_LOCAL_DIR "redis_aof_${Timestamp}.aof"
        Copy-Item $AofFile $AofBackup
        $AofHash = (Get-FileHash -Algorithm SHA256 $AofBackup).Hash.ToLower()
        Set-Content -Path "${AofBackup}.sha256" -Value $AofHash -NoNewline
        Write-Host "Redis AOF backed up: $AofBackup"
    } else {
        Write-Host "WARNING: BACKUP_REDIS_AOF=true but $AofFile not found"
    }
}

$Hash = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLower()
Set-Content -Path $ChecksumFile -Value $Hash -NoNewline
Write-Host "Checksum: $Hash"

if (-not [string]::IsNullOrEmpty($BACKUP_S3_BUCKET)) {
    $Prefix = if ($BACKUP_S3_PREFIX) { $BACKUP_S3_PREFIX } else { 'config-backups' }
    $S3Key  = "${Prefix}/$(Split-Path $Archive -Leaf)"
    & aws s3 cp $Archive "s3://${BACKUP_S3_BUCKET}/${S3Key}" --no-progress
    & aws s3 cp $ChecksumFile "s3://${BACKUP_S3_BUCKET}/${S3Key}.sha256" --no-progress
    Write-Host "S3 upload complete"
}

Write-Host "BACKUP_FILE=$Archive"
Write-Host "Configuration backup finished successfully"
