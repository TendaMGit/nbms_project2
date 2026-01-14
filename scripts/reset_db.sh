#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

require_env() {
  local var="$1"
  if [ -z "${!var:-}" ]; then
    echo "Missing required env var: $var" >&2
    exit 1
  fi
}

is_true() {
  case "${1,,}" in
    1|true|yes) return 0 ;;
    *) return 1 ;;
  esac
}

ENVIRONMENT="${ENVIRONMENT:-dev}"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-}"

if [ "$ENVIRONMENT" = "prod" ] || [[ "$DJANGO_SETTINGS_MODULE" == *".prod"* ]]; then
  echo "Refusing to drop databases in production settings." >&2
  exit 1
fi

NBMS_DB_NAME="${NBMS_DB_NAME:-nbms_project_db2}"
NBMS_TEST_DB_NAME="${NBMS_TEST_DB_NAME:-test_nbms_project_db2}"
NBMS_DB_USER="${NBMS_DB_USER:-nbms_user}"

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
NBMS_DB_PASSWORD="${NBMS_DB_PASSWORD:?NBMS_DB_PASSWORD is required}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

echo "About to drop and recreate:"
echo "- main DB: $NBMS_DB_NAME"
echo "- test DB: $NBMS_TEST_DB_NAME"

if [ "${CONFIRM_DROP:-}" != "YES" ]; then
  echo "Refusing to drop databases without CONFIRM_DROP=YES" >&2
  exit 1
fi

USE_S3="${USE_S3:-0}"
if is_true "$USE_S3"; then
  require_env "S3_ACCESS_KEY"
  require_env "S3_SECRET_KEY"
fi

ENABLE_GEOSERVER="${ENABLE_GEOSERVER:-0}"
if is_true "$ENABLE_GEOSERVER"; then
  require_env "GEOSERVER_PASSWORD"
fi

USE_DOCKER="${USE_DOCKER:-1}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker/docker-compose.yml}"

if [ "$USE_DOCKER" = "1" ]; then
  docker compose -f "$COMPOSE_FILE" up -d postgis
  PSQL_BASE=(docker compose -f "$COMPOSE_FILE" exec -T postgis env PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres)
else
  export PGPASSWORD="$POSTGRES_PASSWORD"
  PSQL_BASE=(psql -U "$POSTGRES_USER" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -d postgres)
fi

"${PSQL_BASE[@]}" \
  -v NBMS_DB_NAME="$NBMS_DB_NAME" \
  -v NBMS_TEST_DB_NAME="$NBMS_TEST_DB_NAME" \
  -v NBMS_DB_USER="$NBMS_DB_USER" <<'SQL'
SELECT format('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %L', :'NBMS_DB_NAME') \gexec
SELECT format('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %L', :'NBMS_TEST_DB_NAME') \gexec

SELECT format('DROP DATABASE IF EXISTS %I', :'NBMS_DB_NAME') \gexec
SELECT format('DROP DATABASE IF EXISTS %I', :'NBMS_TEST_DB_NAME') \gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'NBMS_DB_NAME', :'NBMS_DB_USER') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'NBMS_TEST_DB_NAME', :'NBMS_DB_USER') \gexec
SQL

for db in "$NBMS_DB_NAME" "$NBMS_TEST_DB_NAME"; do
  if [ "$USE_DOCKER" = "1" ]; then
    docker compose -f "$COMPOSE_FILE" exec -T postgis env PGPASSWORD="$POSTGRES_PASSWORD" \
      psql -U "$POSTGRES_USER" -d "$db" <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SQL
  else
    psql -U "$POSTGRES_USER" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -d "$db" <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SQL
  fi
done

PYTHON_BIN="${PYTHON_BIN:-python}"
VENV_PATH="${VENV_PATH:-$ROOT_DIR/.venv}"
if [ -x "$VENV_PATH/bin/python" ]; then
  PYTHON="$VENV_PATH/bin/python"
else
  PYTHON="$PYTHON_BIN"
fi

"$PYTHON" "$ROOT_DIR/manage.py" migrate --noinput
