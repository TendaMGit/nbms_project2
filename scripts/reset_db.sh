#!/usr/bin/env bash
set -euo pipefail

if [ "${CONFIRM_DROP:-}" != "YES" ]; then
  echo "Refusing to drop databases without CONFIRM_DROP=YES" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

NBMS_DB_NAME="${NBMS_DB_NAME:-nbms_project_db2}"
NBMS_TEST_DB_NAME="${NBMS_TEST_DB_NAME:-test_nbms_project_db2}"
NBMS_DB_USER="${NBMS_DB_USER:-nbms_user}"

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

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
