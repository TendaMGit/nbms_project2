#!/usr/bin/env sh
set -eu

OUTPUT_DIR="${1:-backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTPUT_DIR"

DB_NAME="${NBMS_DB_NAME:-nbms_project_db2}"
PG_USER="${POSTGRES_USER:-postgres}"
DB_BACKUP="$OUTPUT_DIR/postgis-$TIMESTAMP.sql"
S3_BACKUP="$OUTPUT_DIR/minio-$TIMESTAMP.tgz"

echo "Creating PostGIS backup: $DB_BACKUP"
docker compose exec -T postgis pg_dump -U "$PG_USER" -d "$DB_NAME" > "$DB_BACKUP"

echo "Creating MinIO data archive: $S3_BACKUP"
docker compose exec -T minio sh -c "tar -czf - -C /data ." > "$S3_BACKUP"

echo "Backup complete."
