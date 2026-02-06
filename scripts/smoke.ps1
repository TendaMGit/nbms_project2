param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health/" -TimeoutSec 10
if ($health.status -ne "ok") {
    throw "Health check failed: /health/ returned status '$($health.status)'."
}

$storage = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health/storage/" -TimeoutSec 10

Write-Host "health.status=$($health.status)"
Write-Host "health_storage.status=$($storage.status)"
if ($storage.detail) {
    Write-Host "health_storage.detail=$($storage.detail)"
}

