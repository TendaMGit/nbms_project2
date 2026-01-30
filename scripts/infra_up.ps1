param(
    [switch]$IncludeGeoServer
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

$services = @("postgis", "redis", "minio", "minio-init")
if ($IncludeGeoServer) { $services += "geoserver" }

Write-Host "Starting infrastructure services: $($services -join ', ')"

docker compose -f docker/docker-compose.yml --env-file .env up -d $services
