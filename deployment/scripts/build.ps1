# =============================================================================
# RestaurantFlow — build.ps1
# Phase 23: Build backend and frontend Docker images (Windows).
# Usage: .\deployment\scripts\build.ps1 [-ImageTag <tag>]
# =============================================================================
param([string]$ImageTag = "")
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Resolve-Path "$ScriptDir\..\.."

if (-not $ImageTag) {
    $ImageTag = (git -C $RepoRoot rev-parse --short HEAD).Trim()
}

$GhcrOwner = if ($env:GHCR_OWNER) { $env:GHCR_OWNER } else { "restaurantflow" }

Write-Host "Building images with tag: $ImageTag"

docker build -t "ghcr.io/$GhcrOwner/restaurantflow-backend:$ImageTag" "$RepoRoot\backend"

$ViteApiUrl = if ($env:VITE_API_URL) { $env:VITE_API_URL } else { "https://yourdomain.com/api" }
$ViteWsUrl  = if ($env:VITE_WS_URL)  { $env:VITE_WS_URL  } else { "wss://yourdomain.com" }

docker build `
    --build-arg "VITE_API_URL=$ViteApiUrl" `
    --build-arg "VITE_WS_URL=$ViteWsUrl" `
    --build-arg "VITE_APP_NAME=RestaurantFlow" `
    -t "ghcr.io/$GhcrOwner/restaurantflow-frontend:$ImageTag" `
    "$RepoRoot\frontend"

Write-Host "Build complete: $ImageTag"
