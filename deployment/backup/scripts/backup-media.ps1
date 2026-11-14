# =============================================================================
# RestaurantFlow — Media Files Backup Script (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Require-Env {
    param([string]$Name)
    $val = [System.Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrEmpty($val)) { throw "Required environment variable $Name is not set." }
    return $val
}

$MEDIA_DIR        = Require-Env 'MEDIA_DIR'
$BACKUP_LOCAL_DIR = Require-Env 'BACKUP_LOCAL_DIR'
$BACKUP_S3_BUCKET = [System.Environment]::GetEnvironmentVariable('BACKUP_S3_BUCKET')
$BACKUP_S3_PREFIX = [System.Environment]::GetEnvironmentVariable('BACKUP_S3_PREFIX')
if ([string]::IsNullOrEmpty($BACKUP_S3_PREFIX)) { $BACKUP_S3_PREFIX = 'media-backups' }

if (-not (Test-Path $MEDIA_DIR)) { throw "MEDIA_DIR does not exist: $MEDIA_DIR" }
New-Item -ItemType Directory -Force -Path $BACKUP_LOCAL_DIR | Out-Null

$Timestamp = (Get-Date -Format 'yyyyMMddTHHmmssZ')
$Archive   = Join-Path $BACKUP_LOCAL_DIR "media_${Timestamp}.tar.gz"
$ChecksumFile = "${Archive}.sha256"

if (Test-Path $Archive) { throw "Backup file already exists: $Archive" }

Write-Host "Starting media backup: MEDIA_DIR=$MEDIA_DIR"

# Use tar if available (Git Bash / WSL); fallback to Compress-Archive for zip
if (Get-Command tar -ErrorAction SilentlyContinue) {
    $MediaParent = Split-Path $MEDIA_DIR -Parent
    $MediaLeaf   = Split-Path $MEDIA_DIR -Leaf
    & tar -czf $Archive -C $MediaParent $MediaLeaf
    if ($LASTEXITCODE -ne 0) { throw "tar failed with exit code $LASTEXITCODE" }
} else {
    # Fallback: zip the directory
    $ZipFile = $Archive -replace '\.tar\.gz$', '.zip'
    Compress-Archive -Path "$MEDIA_DIR\*" -DestinationPath $ZipFile
    $Archive = $ZipFile
    $ChecksumFile = "${Archive}.sha256"
}

if (-not (Test-Path $Archive) -or (Get-Item $Archive).Length -eq 0) {
    throw "Media archive is empty or missing: $Archive"
}

$Hash = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLower()
Set-Content -Path $ChecksumFile -Value $Hash -NoNewline
Write-Host "Checksum: $Hash"

if (-not [string]::IsNullOrEmpty($BACKUP_S3_BUCKET)) {
    $S3Key = "${BACKUP_S3_PREFIX}/$(Split-Path $Archive -Leaf)"
    & aws s3 cp $Archive "s3://${BACKUP_S3_BUCKET}/${S3Key}" --no-progress --storage-class STANDARD_IA
    & aws s3 cp $ChecksumFile "s3://${BACKUP_S3_BUCKET}/${S3Key}.sha256" --no-progress
    Write-Host "S3 upload complete"
}

Write-Host "BACKUP_FILE=$Archive"
Write-Host "Media backup finished successfully: $Archive"
