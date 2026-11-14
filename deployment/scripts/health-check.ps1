# =============================================================================
# RestaurantFlow — health-check.ps1
# Phase 23: Poll /health/ready/ until it returns 200 or timeout is reached (Windows).
# Usage: .\deployment\scripts\health-check.ps1
# =============================================================================

$Host_   = if ($env:HEALTH_CHECK_HOST) { $env:HEALTH_CHECK_HOST } else { "localhost" }
$Port    = if ($env:HEALTH_CHECK_PORT) { $env:HEALTH_CHECK_PORT } else { "80" }
$Url     = "http://${Host_}:${Port}/health/ready/"
$MaxWait = 120
$Interval = 5
$Elapsed  = 0

Write-Host "Waiting for $Url to become ready..."

while ($Elapsed -lt $MaxWait) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            Write-Host "Health check passed (HTTP 200)"
            exit 0
        }
    } catch {
        # Connection refused or non-200 — keep waiting
    }
    Write-Host "Health check failed — retrying in ${Interval}s (${Elapsed}s elapsed)"
    Start-Sleep -Seconds $Interval
    $Elapsed += $Interval
}

Write-Error "Health check timed out after ${MaxWait}s"
exit 1
