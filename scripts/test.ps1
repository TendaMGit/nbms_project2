param(
    [switch]$NoInput,
    [switch]$KeepDb
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot

$pythonBin = [Environment]::GetEnvironmentVariable("PYTHON_BIN")
if (-not $pythonBin) { $pythonBin = "python" }

$venvPath = [Environment]::GetEnvironmentVariable("VENV_PATH")
if (-not $venvPath) { $venvPath = Join-Path $repo ".venv" }

$venvPython = Join-Path $venvPath "Scripts\\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = $pythonBin
}

$testArg = "--keepdb"
if ($NoInput -or $env:CI -eq "1" -or $env:NOINPUT -eq "1") {
    $testArg = "--noinput"
}
if ($KeepDb -or $env:KEEPDB -eq "1") {
    $testArg = "--keepdb"
}

& $python (Join-Path $repo "manage.py") test $testArg

