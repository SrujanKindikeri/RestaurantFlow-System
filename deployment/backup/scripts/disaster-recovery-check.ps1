# =============================================================================
# RestaurantFlow — Disaster Recovery Health Check (PowerShell)
# Phase 25
# =============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$DB_HOST          = [System.Environment]::GetEnvironmentVariable('DB_HOST')
$DB_PORT          = [System.Environment]::GetEnvironmentVariable('DB_PORT')
$DB_USER          = [System.Environment]::GetEnvironmentVariable('DB_USER')
$BACKUP_LOCAL_DIR = [System.Environment]::GetEnvironmentVariable('BACKUP_LOCAL_DIR')
$REDIS_HOST       = [System.Environment]::GetEnvironmentVariable('REDIS_HOST')
$REDIS_PORT       = [System.Environment]::GetEnvironmentVariable('REDIS_PORT')
$REDIS_PASSWORD   = [System.Environment]::GetEnvironmentVariable('REDIS_PASSWORD')
$MAX_AGE_HOURS    = [System.Environment]::GetEnvironmentVariable('BACKUP_MAX_AGE_HOURS')
$MIN_DISK_GB      = [System.Environment]::GetEnvironmentVariable('BACKUP_DISK_MIN_GB')

if ([string]::IsNullOrEmpty($DB_HOST))          { throw "DB_HOST must be set." }
if ([string]::IsNullOrEmpty($DB_PORT))          { throw "DB_PORT must be set." }
if ([string]::IsNullOrEmpty($DB_USER))          { throw "DB_USER must be set." }
if ([string]::IsNullOrEmpty($BACKUP_LOCAL_DIR)) { throw "BACKUP_LOCAL_DIR must be set." }

if ([string]::IsNullOrEmpty($REDIS_HOST))    { $REDIS_HOST = 'localhost' }
if ([string]::IsNullOrEmpty($REDIS_PORT))    { $REDIS_PORT = '6379' }
if ([string]::IsNullOrEmpty($MAX_AGE_HOURS)) { $MAX_AGE_HOURS = '25' }
if ([string]::IsNullOrEmpty($MIN_DISK_GB))   { $MIN_DISK_GB = '5' }

$MaxAgeHours = [int]$MAX_AGE_HOURS
$MinDiskGB   = [int]$MIN_DISK_GB
$Pass        = 0
$Fail        = 0

function Check-Pass { param($Msg) Write-Host "  [PASS] $Msg"; $script:Pass++ }
function Check-Fail { param($Msg) Write-Error "  [FAIL] $Msg"; $script:Fail++ }

Write-Host "=============================="
Write-Host "RestaurantFlow DR Health Check"
Write-Host "=============================="

# 1. PostgreSQL
Write-Host "`n[1] PostgreSQL connectivity"
try {
    $pgResult = & pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER -q 2>&1
    if ($LASTEXITCODE -eq 0) {
        Check-Pass "PostgreSQL accepting connections at ${DB_HOST}:${DB_PORT}"
    } else {
        Check-Fail "PostgreSQL NOT ready at ${DB_HOST}:${DB_PORT}"
    }
} catch {
    Check-Fail "pg_isready not available or failed: $_"
}

# 2. Redis
Write-Host "`n[2] Redis connectivity"
try {
    $redisArgs = @('-h', $REDIS_HOST, '-p', $REDIS_PORT)
    if (-not [string]::IsNullOrEmpty($REDIS_PASSWORD)) {
        $redisArgs += @('-a', $REDIS_PASSWORD)
    }
    $ping = & redis-cli @redisArgs ping 2>&1
    if ($ping -match 'PONG') {
        Check-Pass "Redis responding at ${REDIS_HOST}:${REDIS_PORT}"
    } else {
        Check-Fail "Redis NOT responding at ${REDIS_HOST}:${REDIS_PORT}"
    }
} catch {
    Check-Fail "redis-cli not available or failed: $_"
}

# 3. Disk space
Write-Host "`n[3] Backup disk space"
try {
    if (Test-Path $BACKUP_LOCAL_DIR) {
        $Drive = (Split-Path -Qualifier (Resolve-Path $BACKUP_LOCAL_DIR))
        $Disk  = Get-PSDrive ($Drive -replace ':','') -ErrorAction SilentlyContinue
        if ($Disk) {
            $FreeGB = [math]::Round($Disk.Free / 1GB, 1)
            if ($FreeGB -ge $MinDiskGB) {
                Check-Pass "Backup volume has ${FreeGB}GB available (min: ${MinDiskGB}GB)"
            } else {
                Check-Fail "Low disk: ${FreeGB}GB available (min: ${MinDiskGB}GB)"
            }
        } else {
            Check-Fail "Cannot determine disk space for: $BACKUP_LOCAL_DIR"
        }
    } else {
        Check-Fail "BACKUP_LOCAL_DIR does not exist: $BACKUP_LOCAL_DIR"
    }
} catch {
    Check-Fail "Disk check failed: $_"
}

# 4. Backup freshness
Write-Host "`n[4] Backup freshness"
try {
    $LatestBackup = Get-ChildItem -Path $BACKUP_LOCAL_DIR -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^db_' } |
        Sort-Object FullName | Select-Object -Last 1
    if ($LatestBackup) {
        $AgeHours = [math]::Round(((Get-Date) - $LatestBackup.LastWriteTime).TotalHours, 1)
        if ($AgeHours -lt $MaxAgeHours) {
            Check-Pass "Most recent backup is ${AgeHours}h old (max: ${MaxAgeHours}h)"
        } else {
            Check-Fail "Most recent backup is ${AgeHours}h old (max: ${MaxAgeHours}h)"
        }
    } else {
        Check-Fail "No database backup files found in $BACKUP_LOCAL_DIR"
    }
} catch {
    Check-Fail "Freshness check failed: $_"
}

Write-Host "`n=============================="
Write-Host "Results: $Pass passed, $Fail failed"
Write-Host "=============================="

if ($Fail -gt 0) { exit 1 }
exit 0
