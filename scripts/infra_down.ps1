param(
    [switch]$ResetVolumes
)

$ErrorActionPreference = "Stop"

try {
    docker info | Out-Null
} catch {
    Write-Error "Docker does not appear to be running. Start Docker Desktop and try again."
    exit 1
}

$verify = & powershell -ExecutionPolicy Bypass -File scripts/verify_env.ps1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Stopping infrastructure services..."
if ($ResetVolumes) {
    docker compose -f docker/docker-compose.yml --env-file .env down -v
} else {
    docker compose -f docker/docker-compose.yml --env-file .env down
}
