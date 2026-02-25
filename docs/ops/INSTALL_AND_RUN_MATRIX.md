# Install and Run Matrix

Date: 2026-02-25
Branch baseline: `chore/align-blueprint-2026Q1`

## 1) Windows Local (no GIS)

Use this when you need fast API/frontend iteration without PostGIS binaries.

Prerequisites:
- Python 3.12+
- Node 22+
- `npm` 11+
- `pip` and virtualenv

Environment:
- `ENABLE_GIS=false`
- `DJANGO_SETTINGS_MODULE=config.settings.dev`
- `PYTHONPATH=src`
- SQLite or local PostgreSQL from `.env`

Commands:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

$env:ENABLE_GIS='false'
$env:PYTHONPATH='src'
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

npm --prefix frontend ci
npm --prefix frontend start
```

Ports:
- Backend: `8000`
- Frontend dev server: `4200`

Health checks:
- `http://127.0.0.1:8000/health/`
- `http://127.0.0.1:8000/healthz/`
- `http://127.0.0.1:8000/readyz/`

Troubleshooting:
- `ImportError: config` during pytest: set `PYTHONPATH=src`.
- GIS import errors on Windows: keep `ENABLE_GIS=false` for local non-spatial work.

## 2) Docker Dev (`compose.yml`)

Use this for full local stack with PostGIS, Redis, MinIO, frontend proxy.

Prerequisites:
- Docker Desktop
- `.env` created from `.env.example`

Commands:
```bash
cp .env.example .env
# set required secrets in .env

docker compose --profile minimal up -d --build
# optional: full spatial stack
# docker compose --profile spatial up -d --build
```

Ports:
- Backend: `8000`
- Frontend (nginx): `8081`
- PostGIS: `5432`
- Redis: `6379`
- MinIO API: `9000`
- MinIO console: `9001`
- GeoServer (spatial profile): `8080`

Health checks:
- `curl -fsS http://127.0.0.1:8000/health/`
- `curl -fsS http://127.0.0.1:8081/`
- `curl -fsS http://127.0.0.1:8000/api/system/health`

Troubleshooting:
- `403` from API endpoints: verify session auth and CSRF bootstrap (`/api/auth/csrf`).
- Slow startup: wait for PostGIS health and migration completion.

## 3) Docker Prod Baseline (`docker-compose.prod.yml`)

Use this as production-like baseline (gunicorn + nginx reverse proxy).

Prerequisites:
- Docker host with persistent volumes
- Hardened `.env` (`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, DB creds)

Commands:
```bash
cp .env.example .env
# set production env vars

docker compose -f docker-compose.prod.yml up -d --build
```

Ports:
- Nginx: `80`
- Internal app: `8000` (not published)

Health checks:
- `curl -fsS http://127.0.0.1/healthz/`
- `curl -fsS http://127.0.0.1/readyz/`

Troubleshooting:
- If `check --deploy` fails, verify required production env vars and trusted origins.
- If static assets missing, confirm `collectstatic` executed in app entrypoint.

## 4) Verification Stack (`docker-compose.verify.yml`)

Use this for deterministic integration checks in CI-like mode.

Prerequisites:
- Docker

Commands:
```bash
docker compose -f docker-compose.verify.yml up -d db

docker compose -f docker-compose.verify.yml run --rm app python manage.py check
docker compose -f docker-compose.verify.yml run --rm app pytest -q

docker compose -f docker-compose.verify.yml down -v
```

Ports:
- Verification DB forward: `${NBMS_DB_PORT_FORWARD:-5433}`

Troubleshooting:
- Test DB creation errors: ensure `NBMS_TEST_DB_NAME` is set and writable.
- Container import errors: verify mounted repo path and `PYTHONPATH=/app/src`.

## 5) Observability Add-on (optional)

Run alongside dev/prod compose when needed:
```bash
docker compose -f compose.yml -f docker-compose.observability.yml --profile minimal --profile observability up -d
```

Ports:
- Prometheus: `9090`
- Loki: `3100`
- Grafana: `3000`
