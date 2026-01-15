#!/usr/bin/env bash
set -euo pipefail

if [ "${CONFIRM_DROP_TEST:-}" != "YES" ]; then
  echo "Refusing to drop test DB. Set CONFIRM_DROP_TEST=YES to proceed." >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

PYTHON_BIN="${PYTHON_BIN:-python}"
VENV_PATH="${VENV_PATH:-$ROOT_DIR/.venv}"
if [ -x "$VENV_PATH/bin/python" ]; then
  PYTHON="$VENV_PATH/bin/python"
else
  PYTHON="$PYTHON_BIN"
fi

PYTHONPATH="$ROOT_DIR/src" "$PYTHON" "$ROOT_DIR/manage.py" shell -c "import sys; exec(sys.stdin.read())" <<'PY'
import os
from django.conf import settings

import psycopg2

db = settings.DATABASES["default"]
test_db = db.get("TEST", {}).get("NAME")
main_db = db.get("NAME")

if not test_db:
    raise SystemExit("Test DB name not set.")
if test_db == main_db:
    raise SystemExit("Refusing to drop test DB: same as main DB.")

connect_db = os.environ.get("POSTGRES_DB", "postgres")
if connect_db == test_db:
    connect_db = "postgres"
if connect_db == test_db:
    raise SystemExit("Refusing to connect to the test DB for drop.")

conn = psycopg2.connect(
    dbname=connect_db,
    user=db.get("USER"),
    password=db.get("PASSWORD"),
    host=db.get("HOST"),
    port=db.get("PORT"),
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (test_db,))
    cur.execute(f'DROP DATABASE IF EXISTS "{test_db}"')
print(f"Dropped test DB: {test_db}")
PY
