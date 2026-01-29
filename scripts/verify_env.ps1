param(
    [string]$EnvFile = ".env",
    [string]$ComposeFile = "docker/docker-compose.yml"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Missing .env file."
    Write-Error "Windows: copy .env.local.example .env"
    Write-Error "Linux/macOS: cp .env.local.example .env"
    exit 2
}

if (-not (Test-Path $ComposeFile)) {
    Write-Error "Compose file not found: $ComposeFile"
    exit 2
}

python scripts/verify_env.py --env-file $EnvFile --compose $ComposeFile
exit $LASTEXITCODE
