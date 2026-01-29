#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.test}
export PYTHONPATH=${PYTHONPATH:-/app/src}

python - <<PY
import os
import time
import psycopg2
from psycopg2 import sql

name = os.environ.get("NBMS_DB_NAME")
user = os.environ.get("NBMS_DB_USER")
password = os.environ.get("NBMS_DB_PASSWORD")
host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
admin_db = os.environ.get("POSTGRES_ADMIN_DB", "postgres")

for attempt in range(60):
    try:
        conn = psycopg2.connect(dbname=admin_db, user=user, password=password, host=host, port=port)
        conn.close()
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit("Database did not become ready in time.")

conn = psycopg2.connect(dbname=admin_db, user=user, password=password, host=host, port=port)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (name,))
cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}" ).format(sql.Identifier(name)))
cur.execute(sql.SQL("CREATE DATABASE {}" ).format(sql.Identifier(name)))
cur.close()
conn.close()
PY

python manage.py migrate
python manage.py check
pytest -q
python manage.py verify_post_migration
