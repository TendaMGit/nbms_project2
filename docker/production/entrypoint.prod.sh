#!/usr/bin/env bash
set -euo pipefail

wait_for_db() {
  python - <<'PY'
import time
from django.db import connections

for attempt in range(1, 31):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        print("Database is reachable.")
        raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001
        if attempt == 30:
            print(f"Database check failed after {attempt} attempts: {exc}")
            raise SystemExit(1)
        time.sleep(2)
PY
}

if [ "${DJANGO_WAIT_FOR_DB:-1}" = "1" ]; then
  wait_for_db
fi

if [ "${DJANGO_RUN_PREDEPLOY_CHECK:-1}" = "1" ]; then
  python manage.py predeploy_check --skip-migrate-check
fi

if [ "${DJANGO_RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${DJANGO_COLLECTSTATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
