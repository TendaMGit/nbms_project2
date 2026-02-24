# Production Hardening Plan

## Summary
This hardening pass establishes a production-ready baseline for the NBMS backend without changing core business workflows.

Architecture baseline:
- Django app (`config.settings.prod`) behind Gunicorn
- Nginx reverse proxy serving `/static/` and `/media/`
- PostgreSQL/PostGIS primary database
- Redis cache/rate-limit backend
- Optional Sentry error monitoring

## Workstream Checklist
- [x] WS1 Environment and settings hygiene
  - `django-environ` adopted for settings parsing
  - Production env contract enforced (`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`)
  - Prod settings fail-fast tests added
- [x] WS2 HTTPS/proxy/cookies/security headers/CSP
  - Proxy-aware settings (`SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, `USE_X_FORWARDED_PORT`)
  - Hardened cookie, HSTS, and header defaults
  - CSP + security headers tested
- [x] WS3 Auth hardening and abuse controls
  - Existing login/public API rate limiting coverage expanded
  - DRF throttle configuration standardized
  - CORS guardrails added (no wildcard in prod)
  - Upload/request size limits added
- [x] WS4 Logging, audit, observability
  - Structured request completion/failure logging middleware
  - Request metadata in logs (`request_id`, `user_id`, `path`, `status_code`, `latency_ms`)
  - Sensitive-data log redaction filter
  - Optional Sentry integration (env-gated)
  - `/healthz` and `/readyz` endpoints added
- [x] WS5 Database production baseline
  - `DB_CONN_MAX_AGE` support for URL/fallback DB config
  - Optional PgBouncer-friendly cursor toggle (`DB_DISABLE_SERVER_SIDE_CURSORS`)
  - `predeploy_check` management command added
  - pgBackRest backup/PITR templates added
- [x] WS6 Production server stack
  - Added multi-stage production `Dockerfile`
  - Added `docker-compose.prod.yml`
  - Added `gunicorn.conf.py`
  - Added `nginx/conf.d/nbms.conf`
  - Added production entrypoint (`docker/production/entrypoint.prod.sh`)
- [x] WS7 CI/CD quality gates
  - Added `Makefile` targets (`check`, `test`, `deploy-check`)
  - CI updated for prod deploy checks with required env contract
  - Optional Ruff lint step added

## Implemented Now
- Secure-by-default production settings and strict env validation
- Proxy/HTTPS correctness for reverse-proxied deployment
- Security headers, CSP handling, secure cookie defaults
- Abuse controls (login + API throttles) and CORS restrictions
- Structured logs with request correlation and PII redaction
- Operational probes (`/healthz`, `/readyz`)
- Production container stack (Gunicorn + Nginx + Postgres + Redis)
- Predeploy operational checks and backup/PITR templates
- CI and local Make targets for readiness checks

## Optional / Future Enhancements
- Enforce CSP non-report mode only after staged allowlist validation per environment
- Add OpenTelemetry traces/metrics export pipeline
- Add dedicated secrets manager integration (Vault/AWS Secrets Manager/Azure Key Vault)
- Add blue/green or canary deployment pipeline
- Add PgBouncer container and connection-pool tuning profiles
- Add restore-drill automation in CI/CD or scheduled ops job

## Verification Commands
Run from repository root.

1. Settings and env hardening
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_prod_settings.py
PYTHONPATH=src python manage.py check --settings=config.settings.dev
```

2. Header and cookie hardening
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_security_headers.py
```

3. Throttling / abuse controls
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_rate_limiting.py
```

4. Logging and health probes
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_logging_utils.py src/nbms_app/tests/test_health_checks.py
```

5. Predeploy checks
```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_READ_DOT_ENV_FILE=0 \
DJANGO_SECRET_KEY='replace-me-with-long-secret' \
DATABASE_URL='sqlite:///tmp-predeploy.sqlite3' \
DJANGO_ALLOWED_HOSTS='example.org' \
DJANGO_CSRF_TRUSTED_ORIGINS='https://example.org' \
python manage.py predeploy_check --skip-migrate-check
```

6. Production compose syntax
```bash
docker compose -f docker-compose.prod.yml config
```

## Diff-Friendly New Files
- `docs/production_hardening/current_state.md`
- `docs/production_hardening/production_hardening_plan.md`
- `docs/production_hardening/secure_settings_reference.md`
- `docs/production_hardening/deployment_runbook.md`
- `docs/production_hardening/db_backup_pitr_runbook.md`
- `docs/production_hardening/security_verification.md`
- `Dockerfile`
- `docker-compose.prod.yml`
- `gunicorn.conf.py`
- `nginx/conf.d/nbms.conf`
- `docker/production/entrypoint.prod.sh`
- `scripts/ops/pgbackrest_backup.sh`
- `scripts/ops/pgbackrest_restore_drill.sh`
- `scripts/ops/pgbackrest.cron.example`
- `src/nbms_app/middleware_request_logging.py`
- `src/nbms_app/management/commands/predeploy_check.py`
- `src/nbms_app/tests/test_security_headers.py`
- `src/nbms_app/tests/test_health_checks.py`
- `src/nbms_app/tests/test_logging_utils.py`
- `src/nbms_app/tests/test_predeploy_check_command.py`

## How To Run Production Locally
1. Create env file and set production values:
```bash
cp .env.example .env
# Edit .env: set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS,
# POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
```
2. Start stack:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
3. Verify health:
```bash
curl -fsS http://127.0.0.1/healthz/
curl -fsS http://127.0.0.1/readyz/
```
4. Stop stack:
```bash
docker compose -f docker-compose.prod.yml down -v
```
