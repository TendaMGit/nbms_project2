param(
    [Parameter(Mandatory = $true)]
    [string]$DbBackup,
    [Parameter(Mandatory = $true)]
    [string]$MinioBackup
)

if (!(Test-Path $DbBackup)) {
    throw "Database backup file not found: $DbBackup"
}
if (!(Test-Path $MinioBackup)) {
    throw "MinIO backup file not found: $MinioBackup"
}

$dbName = if ($env:NBMS_DB_NAME) { $env:NBMS_DB_NAME } else { "nbms_project_db2" }
$pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }

Write-Host "Restoring PostGIS from $DbBackup"
Get-Content $DbBackup -Raw | docker compose exec -T postgis psql -U $pgUser -d $dbName

Write-Host "Restoring MinIO data from $MinioBackup"
Get-Content $MinioBackup -Encoding Byte -ReadCount 0 | docker compose exec -T minio sh -c "rm -rf /data/* && tar -xzf - -C /data"

Write-Host "Restore complete."
