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

Import-DotEnv (Join-Path $RootDir ".env")

if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = "config.settings.test"
}

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$VenvPath = if ($env:VENV_PATH) { $env:VENV_PATH } else { Join-Path $RootDir ".venv" }
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { $PythonBin }

$pytestArgs = @()
if ($env:KEEPDB -eq "1") {
    $pytestArgs += "--reuse-db"
}

$env:PYTHONWARNINGS = "default"
& $Python -m pytest @pytestArgs