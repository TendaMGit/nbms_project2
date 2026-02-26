# Deployment Runbook

## Scope
Production deployment runbook for the Docker-first NBMS stack (`docker-compose.prod.yml`).

## Components
- `nginx` reverse proxy (public entrypoint)
- `app` Django + Gunicorn
- `db` PostgreSQL/PostGIS
- `redis` cache/rate-limit backend

## Prerequisites
- Docker Engine + Compose plugin
- `.env` file with production values
- DNS/LB pointed at host (or upstream LB if TLS terminated externally)

## Required Environment Values
At minimum set:
- `DJANGO_SECRET_KEY`
- `DATABASE_URL` (auto-built in compose but keep explicit in production tooling)
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

## First Deployment
1. Prepare environment file:
```bash
cp .env.example .env
# Edit production values
```
2. Validate compose file:
```bash
docker compose -f docker-compose.prod.yml config
```
3. Start services:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
4. Verify readiness:
```bash
curl -fsS http://127.0.0.1/healthz/
curl -fsS http://127.0.0.1/readyz/
```

## Rolling Update
1. Pull latest code and images.
2. Rebuild and restart app/proxy:
```bash
docker compose -f docker-compose.prod.yml up -d --build app nginx
```
3. Watch logs and probes:
```bash
docker compose -f docker-compose.prod.yml logs -f --tail=200 app nginx
curl -fsS http://127.0.0.1/readyz/
```

## Pre-Deploy Gate
Run before release:
```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_READ_DOT_ENV_FILE=0 \
DJANGO_SECRET_KEY='...' DATABASE_URL='...' DJANGO_ALLOWED_HOSTS='...' \
DJANGO_CSRF_TRUSTED_ORIGINS='...' python manage.py predeploy_check
```

## Secret Generation and Rotation
Generate a Django secret key:
```bash
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```
Rotation process:
1. Generate new secret value in secret manager.
2. Update runtime env for app.
3. Redeploy app container.
4. Validate `/healthz/`, `/readyz/`, and auth/session behavior.

Notes:
- `SECRET_KEY` rotation invalidates existing sessions; schedule a maintenance window if needed.
- Rotate DB credentials by coordinated DB role update + env update + restart.

## Backup and Restore
- Follow `docs/production_hardening/db_backup_pitr_runbook.md`.
- Backup script template: `scripts/ops/pgbackrest_backup.sh`
- Restore drill template: `scripts/ops/pgbackrest_restore_drill.sh`

## Logs and Monitoring
Tail logs:
```bash
docker compose -f docker-compose.prod.yml logs -f --tail=200 app nginx db redis
```

App request logs include:
- `request_id`
- `user_id`
- `path`
- `status_code`
- `latency_ms`

Enable Sentry by setting `SENTRY_DSN` and sample-rate env vars.

## Troubleshooting
- App unhealthy:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=200 app
```
- DB connectivity issue:
```bash
docker compose -f docker-compose.prod.yml logs --tail=200 db
```
- Migration drift:
```bash
PYTHONPATH=src python manage.py migrate --check
```
- Header/proxy issues:
```bash
curl -I http://127.0.0.1/healthz/
```

## Rollback
1. Revert to prior image/tag and compose references.
2. Restart app/nginx.
3. Validate probes and key user journeys.
4. If DB rollback needed, execute PITR per DB runbook.
