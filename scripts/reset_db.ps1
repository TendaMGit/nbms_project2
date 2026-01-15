$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $pair = $line.Split("=", 2)
        if ($pair.Count -lt 2) {
            return
        }
        $name = $pair[0].Trim()
        $value = $pair[1].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($null -eq [System.Environment]::GetEnvironmentVariable($name)) {
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Require-Env {
    param([string]$Name)
    if ($null -eq [System.Environment]::GetEnvironmentVariable($Name)) {
        Write-Error "Missing required env var: $Name"
        exit 1
    }
}

function Is-True {
    param([string]$Value)
    if (-not $Value) {
        return $false
    }
    switch ($Value.ToLower()) {
        "1" { return $true }
        "true" { return $true }
        "yes" { return $true }
        default { return $false }
    }
}

Import-DotEnv (Join-Path $RootDir ".env")

$environment = $env:ENVIRONMENT
$settingsModule = $env:DJANGO_SETTINGS_MODULE
if ($environment -eq "prod" -or ($settingsModule -and $settingsModule -like "*.prod*")) {
    Write-Error "Refusing to drop databases in production settings."
    exit 1
}

$NBMS_DB_NAME = if ($env:NBMS_DB_NAME) { $env:NBMS_DB_NAME } else { "nbms_project_db2" }
$NBMS_TEST_DB_NAME = if ($env:NBMS_TEST_DB_NAME) { $env:NBMS_TEST_DB_NAME } else { "test_nbms_project_db2" }
$NBMS_DB_USER = if ($env:NBMS_DB_USER) { $env:NBMS_DB_USER } else { "nbms_user" }

$POSTGRES_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$POSTGRES_PASSWORD = $env:POSTGRES_PASSWORD
$NBMS_DB_PASSWORD = $env:NBMS_DB_PASSWORD
$POSTGRES_HOST = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$POSTGRES_PORT = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }

Require-Env "POSTGRES_PASSWORD"
Require-Env "NBMS_DB_PASSWORD"

Write-Host "About to drop and recreate:"
Write-Host "- main DB: $NBMS_DB_NAME"
Write-Host "- test DB: $NBMS_TEST_DB_NAME"

if ($env:CONFIRM_DROP -ne "YES") {
    Write-Error "Refusing to drop databases without CONFIRM_DROP=YES"
    exit 1
}

$useS3 = if ($env:USE_S3) { $env:USE_S3 } else { "0" }
if (Is-True $useS3) {
    Require-Env "S3_ACCESS_KEY"
    Require-Env "S3_SECRET_KEY"
}

$enableGeo = if ($env:ENABLE_GEOSERVER) { $env:ENABLE_GEOSERVER } else { "0" }
if (Is-True $enableGeo) {
    Require-Env "GEOSERVER_PASSWORD"
}

$UseDocker = if ($env:USE_DOCKER) { $env:USE_DOCKER } else { "1" }
$ComposeFile = if ($env:COMPOSE_FILE) { $env:COMPOSE_FILE } else { Join-Path $RootDir "docker\docker-compose.yml" }

$dropSql = @"
SELECT format('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %L', :'NBMS_DB_NAME') \gexec
SELECT format('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %L', :'NBMS_TEST_DB_NAME') \gexec

SELECT format('DROP DATABASE IF EXISTS %I', :'NBMS_DB_NAME') \gexec
SELECT format('DROP DATABASE IF EXISTS %I', :'NBMS_TEST_DB_NAME') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'NBMS_DB_NAME', :'NBMS_DB_USER') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'NBMS_TEST_DB_NAME', :'NBMS_DB_USER') \gexec
"@

if ($UseDocker -eq "1") {
    docker compose -f $ComposeFile up -d postgis
    $dropSql | docker compose -f $ComposeFile exec -T postgis env PGPASSWORD=$POSTGRES_PASSWORD `
        psql -U $POSTGRES_USER -d postgres -v NBMS_DB_NAME=$NBMS_DB_NAME `
        -v NBMS_TEST_DB_NAME=$NBMS_TEST_DB_NAME -v NBMS_DB_USER=$NBMS_DB_USER
} else {
    $env:PGPASSWORD = $POSTGRES_PASSWORD
    $dropSql | psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d postgres `
        -v NBMS_DB_NAME=$NBMS_DB_NAME -v NBMS_TEST_DB_NAME=$NBMS_TEST_DB_NAME `
        -v NBMS_DB_USER=$NBMS_DB_USER
}

$extSql = @"
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
"@

foreach ($db in @($NBMS_DB_NAME, $NBMS_TEST_DB_NAME)) {
    if ($UseDocker -eq "1") {
        $extSql | docker compose -f $ComposeFile exec -T postgis env PGPASSWORD=$POSTGRES_PASSWORD `
            psql -U $POSTGRES_USER -d $db
    } else {
        $env:PGPASSWORD = $POSTGRES_PASSWORD
        $extSql | psql -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_PORT -d $db
    }
}

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$VenvPath = if ($env:VENV_PATH) { $env:VENV_PATH } else { Join-Path $RootDir ".venv" }
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $PythonBin }

& $Python (Join-Path $RootDir "manage.py") migrate --noinput
