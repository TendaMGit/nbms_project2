param(
    [string]$OutputDir = "backups"
)

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$dbName = if ($env:NBMS_DB_NAME) { $env:NBMS_DB_NAME } else { "nbms_project_db2" }
$pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$dbBackup = Join-Path $OutputDir "postgis-$timestamp.sql"
$s3Backup = Join-Path $OutputDir "minio-$timestamp.tgz"

Write-Host "Creating PostGIS backup: $dbBackup"
docker compose exec -T postgis pg_dump -U $pgUser -d $dbName > $dbBackup

Write-Host "Creating MinIO data archive: $s3Backup"
docker compose exec -T minio sh -c "tar -czf - -C /data ." > $s3Backup

Write-Host "Backup complete."
