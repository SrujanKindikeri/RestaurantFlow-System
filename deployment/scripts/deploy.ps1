# =============================================================================
# RestaurantFlow — deploy.ps1
# Phase 23: Pull images, run migrations, restart services, verify health (Windows).
# Usage: .\deployment\scripts\deploy.ps1 [-ImageTag <tag>]
# =============================================================================
param([string]$ImageTag = "latest")
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path "$ScriptDir\..\.."

Write-Host "=== Deploying RestaurantFlow: $ImageTag ==="

& "$ScriptDir\validate-environment.ps1"
& "$ScriptDir\backup-before-deploy.ps1"

$env:IMAGE_TAG = $ImageTag

docker compose `
    -f "$RepoRoot\docker-compose.yml" `
    -f "$RepoRoot\docker-compose.prod.yml" `
    pull backend nginx

docker compose `
    -f "$RepoRoot\docker-compose.yml" `
    -f "$RepoRoot\docker-compose.prod.yml" `
    run --rm backend python manage.py migrate --noinput

docker compose `
    -f "$RepoRoot\docker-compose.yml" `
    -f "$RepoRoot\docker-compose.prod.yml" `
    up -d --no-build

& "$ScriptDir\health-check.ps1"

Write-Host "=== Deployment complete: $ImageTag ==="
