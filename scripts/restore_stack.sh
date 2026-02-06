#!/usr/bin/env sh
set -eu

if [ $# -lt 2 ]; then
  echo "Usage: scripts/restore_stack.sh <db_backup.sql> <minio_backup.tgz>"
  exit 1
fi

DB_BACKUP="$1"
MINIO_BACKUP="$2"

if [ ! -f "$DB_BACKUP" ]; then
  echo "Database backup file not found: $DB_BACKUP" >&2
  exit 1
fi
if [ ! -f "$MINIO_BACKUP" ]; then
  echo "MinIO backup file not found: $MINIO_BACKUP" >&2
  exit 1
fi

DB_NAME="${NBMS_DB_NAME:-nbms_project_db2}"
PG_USER="${POSTGRES_USER:-postgres}"

echo "Restoring PostGIS from $DB_BACKUP"
cat "$DB_BACKUP" | docker compose exec -T postgis psql -U "$PG_USER" -d "$DB_NAME"

echo "Restoring MinIO data from $MINIO_BACKUP"
cat "$MINIO_BACKUP" | docker compose exec -T minio sh -c "rm -rf /data/* && tar -xzf - -C /data"

echo "Restore complete."
