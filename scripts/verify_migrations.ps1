param(
    [switch]$KeepAlive
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
$composeFile = Join-Path $repo "docker-compose.verify.yml"
$envFile = Join-Path $repo ".env.verify"
$envExample = Join-Path $repo ".env.verify.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "Created .env.verify from .env.verify.example. Update credentials if needed."
    } else {
        throw "Missing .env.verify and .env.verify.example."
    }
}

function Get-EnvValue($key) {
    $line = Get-Content $envFile | Where-Object { $_ -match "^$key=" } | Select-Object -First 1
    if ($line) {
        return $line.Split("=", 2)[1]
    }
    return $null
}

$dbUser = Get-EnvValue "NBMS_DB_USER"
$dbName = Get-EnvValue "NBMS_DB_NAME"

Write-Host "Starting PostGIS verification DB..."
& docker compose -f $composeFile --env-file $envFile up -d db | Out-Host

Write-Host "Waiting for database readiness..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        & docker compose -f $composeFile --env-file $envFile exec -T db pg_isready -U $dbUser -d $dbName | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
    Start-Sleep -Seconds 2
}
if (-not $ready) {
    throw "Database did not become ready in time."
}

Write-Host "Running migration verification inside Docker..."
& docker compose -f $composeFile --env-file $envFile run --rm app ./scripts/verify_migrations.sh

if (-not $KeepAlive) {
    Write-Host "Tearing down verification stack..."
    & docker compose -f $composeFile --env-file $envFile down -v | Out-Host
} else {
    Write-Host "Keeping containers running (KeepAlive set)."
}
