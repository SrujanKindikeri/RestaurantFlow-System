# =============================================================================
# RestaurantFlow — rollback.ps1
# Phase 23: Pull a previous image tag and restart services (Windows).
# Usage: .\deployment\scripts\rollback.ps1 -PrevTag <previous-image-tag>
# =============================================================================
param([Parameter(Mandatory = $true)][string]$PrevTag)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path "$ScriptDir\..\.."

Write-Host "=== Rolling back to: $PrevTag ==="

$env:IMAGE_TAG = $PrevTag

docker compose `
    -f "$RepoRoot\docker-compose.yml" `
    -f "$RepoRoot\docker-compose.prod.yml" `
    pull backend nginx

docker compose `
    -f "$RepoRoot\docker-compose.yml" `
    -f "$RepoRoot\docker-compose.prod.yml" `
    up -d --no-build

& "$ScriptDir\health-check.ps1"

Write-Host "=== Rollback complete: $PrevTag ==="
Write-Host "NOTE: If migration rollback is needed, run manually:"
Write-Host "  docker compose run --rm backend python manage.py migrate <app> <migration>"
