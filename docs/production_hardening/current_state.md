# Current State Findings

## Scope
Repository: `nbms_project2`  
Date: 2026-02-24

## Current settings layout
- Django settings are already split into a package:
  - `src/config/settings/base.py`
  - `src/config/settings/dev.py`
  - `src/config/settings/prod.py`
  - `src/config/settings/test.py`
- `manage.py` defaults to `config.settings.dev` and switches to `config.settings.test` for test commands.
- `wsgi.py` and `asgi.py` currently default to `config.settings.dev`.

## Current .env usage
- `.env` is loaded in `base.py` via `python-dotenv` (`load_dotenv(BASE_DIR / ".env")`).
- Environment variables currently drive:
  - secret key, debug, hosts, csrf origins
  - database (`DATABASE_URL` and fallback discrete DB vars)
  - redis/cache toggles
  - logging format/level
  - S3 storage toggles
  - rate limits
  - production security toggles (HSTS/SSL redirect/cookies/CSP)
- `.env.example` exists with placeholders and many security-related variables.

## Current middleware and security headers
- Middleware includes:
  - `django.middleware.security.SecurityMiddleware`
  - custom request id middleware (`nbms_app.middleware_request_id.RequestIDMiddleware`)
  - custom rate limit middleware (`nbms_app.middleware.RateLimitMiddleware`)
  - custom metrics middleware
  - custom session fixation mitigation + security headers middleware
- Production settings already enforce several secure defaults:
  - `DEBUG=False`
  - secure cookies, HSTS, SSL redirect, `X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF`, referrer/opener policies
  - CSP value configured via `CONTENT_SECURITY_POLICY` and applied by custom middleware
- Proxy SSL header is configurable and parsed from env in `prod.py`, but trusted proxy behavior and forwarded host hardening are incomplete.

## Current auth and API surface
- DRF is enabled (`rest_framework`, `drf-spectacular`, `django-filter`).
- Auth uses Django session + basic auth for DRF defaults.
- Two-factor packages are installed and wired (`django-otp`, `two_factor`).
- Password validators are enabled in `base.py`.
- Existing rate limiting middleware protects multiple paths including login/password reset/api endpoints.

## Current logging/audit approach
- Logging is configured centrally in `base.py` with plain or JSON formatter (env-controlled).
- Custom request-id logging filter is present.
- JSON formatter currently logs timestamp/level/logger/message/request_id.
- Audit events are domain-level (`AuditEvent`) and management/audit views exist.
- Request path/status/user/latency are not consistently present in structured logs yet.

## Current database configuration
- Database config supports `DATABASE_URL` via `dj_database_url`.
- Fallback supports Postgres/PostGIS env fields; GIS engine auto-switches by `ENABLE_GIS`.
- `conn_max_age=600` is already set in URL parsing path.
- No dedicated production DB readiness/predeploy management command yet.

## Current static/media handling
- Static:
  - `STATIC_URL=/static/`
  - `STATIC_ROOT=staticfiles`
  - `collectstatic` runs in container entrypoint
- Media:
  - local filesystem by default
  - optional S3/MinIO via `django-storages`
- In dev, Django serves media when `DEBUG=True`.

## Current deployment and CI patterns
- Existing Docker assets focus on development and profile-based local stacks:
  - `compose.yml`, `docker/backend/Dockerfile`, `docker/backend/entrypoint.sh`
  - frontend docker/nginx assets for Angular
- Backend container currently runs `runserver` (not gunicorn) in entrypoint.
- No dedicated `docker-compose.prod.yml` + reverse-proxy production scaffold yet.
- CI exists (`.github/workflows/ci.yml`, `migration-verify.yml`) and already includes tests, deploy check, Bandit, pip-audit baseline.

## Production baseline gaps (to implement)
- Explicit production bootstrap files (`Dockerfile` prod, `gunicorn.conf.py`, `docker-compose.prod.yml`, `nginx/conf.d/nbms.conf`, prod entrypoint).
- Stronger environment contract for production-required vars with fail-fast checks.
- Forwarded-proxy correctness hardening (`USE_X_FORWARDED_HOST`, canonical proxy header defaults).
- Formalized security verification tests for headers/cookies/CSP behaviors.
- Standard unauthenticated ops probes (`/healthz`, `/readyz`) with lightweight readiness semantics.
- Request logging enrichment (user/path/status/latency) + PII-safe defaults.
- DB pre-deploy check command and documented zero-downtime migration discipline.
- Dedicated backup + PITR runbook (pgBackRest) and restore-drill checklist.
- Production readiness Make targets and explicit CI target for deploy baseline checks.
