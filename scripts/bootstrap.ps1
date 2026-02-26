param(
    [switch]$CreateVenv,
    [switch]$CreateSuperuser
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $idx = $trimmed.IndexOf("=")
        if ($idx -lt 1) { continue }
        $name = $trimmed.Substring(0, $idx).Trim()
        $value = $trimmed.Substring($idx + 1).Trim()
        if (-not [Environment]::GetEnvironmentVariable($name)) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Test-Truthy([string]$Value) {
    if (-not $Value) { return $false }
    return @("1", "true", "yes") -contains $Value.ToLowerInvariant()
}

function Require-Env([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if (-not $value) {
        throw "Missing required env var: $Name"
    }
}

Import-DotEnv (Join-Path $repo ".env")

Require-Env "POSTGRES_PASSWORD"
Require-Env "NBMS_DB_PASSWORD"

$useS3 = [Environment]::GetEnvironmentVariable("USE_S3")
if (Test-Truthy $useS3) {
    Require-Env "S3_ACCESS_KEY"
    Require-Env "S3_SECRET_KEY"
}

$enableGeoServer = [Environment]::GetEnvironmentVariable("ENABLE_GEOSERVER")
if (Test-Truthy $enableGeoServer) {
    Require-Env "GEOSERVER_PASSWORD"
}

$pythonBin = [Environment]::GetEnvironmentVariable("PYTHON_BIN")
if (-not $pythonBin) { $pythonBin = "python" }

$venvPath = [Environment]::GetEnvironmentVariable("VENV_PATH")
if (-not $venvPath) { $venvPath = Join-Path $repo ".venv" }

if ($CreateVenv -and -not (Test-Path $venvPath)) {
    & $pythonBin -m venv $venvPath
}

$venvPython = Join-Path $venvPath "Scripts\\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = $pythonBin
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $repo "requirements.txt")
& $python (Join-Path $repo "manage.py") migrate --noinput

if ($CreateSuperuser) {
    & $python (Join-Path $repo "manage.py") createsuperuser
}
