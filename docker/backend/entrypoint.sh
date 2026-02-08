#!/bin/sh
set -eu

python - <<'PY'
import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

target_db = os.environ.get("NBMS_DB_NAME", "nbms_project_db2")
admin_db = os.environ.get("POSTGRES_DB", "postgres")
conn = psycopg2.connect(
    dbname=admin_db,
    user=os.environ.get("POSTGRES_USER", "postgres"),
    password=os.environ.get("POSTGRES_PASSWORD", ""),
    host=os.environ.get("POSTGRES_HOST", "postgis"),
    port=os.environ.get("POSTGRES_PORT", "5432"),
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
if not cur.fetchone():
    cur.execute(f'CREATE DATABASE "{target_db}"')
cur.close()
conn.close()
PY

python manage.py migrate --noinput
python manage.py bootstrap_roles
python manage.py seed_reporting_defaults
python manage.py seed_mea_template_packs
python manage.py seed_indicator_workflow_v1
python manage.py seed_demo_spatial
python manage.py seed_programme_ops_v1

if [ "${SYNC_SPATIAL_SOURCES_ON_BOOT:-0}" = "1" ]; then
  python manage.py sync_spatial_sources
fi

DEV_RUNTIME="0"
if [ "${DJANGO_DEBUG:-false}" = "true" ] || [ "${DJANGO_DEBUG:-false}" = "True" ]; then
  DEV_RUNTIME="1"
fi
if [ "${ENVIRONMENT:-dev}" = "dev" ] || [ "${ENVIRONMENT:-dev}" = "test" ]; then
  DEV_RUNTIME="1"
fi

if [ "$DEV_RUNTIME" = "1" ] && [ "${SEED_DEMO_USERS:-0}" = "1" ]; then
  python manage.py seed_demo_users
fi

if [ "$DEV_RUNTIME" = "1" ] && [ -n "${NBMS_ADMIN_USERNAME:-}" ] && [ -n "${NBMS_ADMIN_EMAIL:-}" ] && [ -n "${NBMS_ADMIN_PASSWORD:-}" ]; then
  python manage.py ensure_system_admin
fi

python manage.py collectstatic --noinput

python manage.py runserver 0.0.0.0:8000
