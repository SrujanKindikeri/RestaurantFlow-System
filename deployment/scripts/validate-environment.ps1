# =============================================================================
# RestaurantFlow — validate-environment.ps1
# Phase 23: Confirm required env vars are set before deploying (Windows).
# Usage: .\deployment\scripts\validate-environment.ps1
# =============================================================================
$ErrorActionPreference = "Stop"

$RequiredVars = @(
    "SECRET_KEY",
    "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT",
    "REDIS_URL", "REDIS_PASSWORD",
    "ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"
)

$Missing = @()
foreach ($Var in $RequiredVars) {
    $val = [System.Environment]::GetEnvironmentVariable($Var)
    if ([string]::IsNullOrEmpty($val)) {
        $Missing += $Var
    }
}

if ($Missing.Count -gt 0) {
    Write-Error "Missing required environment variables: $($Missing -join ', ')"
    exit 1
}

$SecretKey = [System.Environment]::GetEnvironmentVariable("SECRET_KEY")
if ($SecretKey -eq "change-me-use-a-50-char-random-string" -or
    $SecretKey -eq "dev-only-insecure-key-DO-NOT-USE-IN-PRODUCTION") {
    Write-Error "SECRET_KEY is set to an insecure default value."
    exit 1
}

Write-Host "Environment validation passed."
