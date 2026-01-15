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

Require-Env "POSTGRES_PASSWORD"
Require-Env "NBMS_DB_PASSWORD"

$useS3 = if ($env:USE_S3) { $env:USE_S3 } else { "0" }
if (Is-True $useS3) {
    Require-Env "S3_ACCESS_KEY"
    Require-Env "S3_SECRET_KEY"
}

$enableGeo = if ($env:ENABLE_GEOSERVER) { $env:ENABLE_GEOSERVER } else { "0" }
if (Is-True $enableGeo) {
    Require-Env "GEOSERVER_PASSWORD"
}

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$VenvPath = if ($env:VENV_PATH) { $env:VENV_PATH } else { Join-Path $RootDir ".venv" }
$CreateVenv = if ($env:CREATE_VENV) { $env:CREATE_VENV } else { "0" }

if ($CreateVenv -eq "1" -and -not (Test-Path $VenvPath)) {
    & $PythonBin -m venv $VenvPath
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $PythonBin }

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $RootDir "requirements.txt")

& $Python (Join-Path $RootDir "manage.py") migrate --noinput

if ($env:CREATE_SUPERUSER -eq "1") {
    & $Python (Join-Path $RootDir "manage.py") createsuperuser
}
