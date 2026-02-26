# Secure Settings Reference

## Purpose
This document maps production-relevant settings to security intent and practical verification steps.

## Core Environment Contract
Required in production:
- `DJANGO_SECRET_KEY`
- `DATABASE_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Fail-fast enforcement is implemented in `config.settings.prod`.

## Settings Matrix

### Runtime and Environment
- `DJANGO_SETTINGS_MODULE=config.settings.prod`
  - Rationale: enforce production-only behavior.
  - Verify: `python -c "import os; print(os.environ.get('DJANGO_SETTINGS_MODULE'))"`
- `DJANGO_DEBUG=false`
  - Rationale: prevent debug data leakage.
  - Verify: `PYTHONPATH=src python -c "import config.settings.prod as s; print(s.DEBUG)"`

### Host and CSRF Trust
- `DJANGO_ALLOWED_HOSTS`
  - Rationale: host header protection.
  - Verify: check non-empty env value and startup succeeds.
- `DJANGO_CSRF_TRUSTED_ORIGINS`
  - Rationale: valid cross-origin CSRF enforcement for trusted frontends.
  - Verify: ensure deployed origins are explicitly listed.

### HTTPS and Proxy Correctness
- `SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https`
- `USE_X_FORWARDED_HOST=true`
- `USE_X_FORWARDED_PORT=true`
- `SECURE_SSL_REDIRECT=true`
- `SECURE_REDIRECT_EXEMPT` (optional explicit exemptions)
  - Rationale: correct scheme/host handling behind LB/reverse proxy.
  - Verify: proxied requests are treated as HTTPS and non-HTTPS redirects are enforced where expected.

### Cookie and Session Security
- `SESSION_COOKIE_SECURE=true`
- `CSRF_COOKIE_SECURE=true`
- `SESSION_COOKIE_HTTPONLY=true`
- `CSRF_COOKIE_HTTPONLY=true`
- `SESSION_COOKIE_SAMESITE=Lax`
- `CSRF_COOKIE_SAMESITE=Lax`
- `SESSION_COOKIE_NAME=nbms_sessionid`
- `SESSION_COOKIE_AGE=43200`
  - Rationale: protect session/CSRF cookies against network and script abuse.
  - Verify: inspect `Set-Cookie` headers for secure flags.

### HSTS and Browser Policy Headers
- `SECURE_HSTS_SECONDS` (default `31536000`)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD` (toggle carefully)
- `SECURE_REFERRER_POLICY=strict-origin-when-cross-origin`
- `X_FRAME_OPTIONS=DENY`
- `PERMISSIONS_POLICY=geolocation=(), camera=(), microphone=(), payment=()`
- `SECURE_CONTENT_TYPE_NOSNIFF=true`
- `SECURE_CROSS_ORIGIN_OPENER_POLICY=same-origin`
  - Rationale: browser-side exploit and data-leak reduction.
  - Verify: `curl -I https://<host>/healthz/` and inspect headers.

### Content Security Policy (CSP)
- `CONTENT_SECURITY_POLICY` (default strict template)
- `CONTENT_SECURITY_POLICY_REPORT_ONLY` (staging rollout support)
  - Rationale: constrain script/style/connect/image origins.
  - Verify: header present as `Content-Security-Policy` or `...-Report-Only`.

### CORS and CSRF Interop
- `CORS_ALLOWED_ORIGINS` (explicit allowlist)
- `CORS_ALLOW_ALL_ORIGINS=false` in prod (enforced)
- `CORS_ALLOW_CREDENTIALS=true`
- `CORS_ALLOW_HEADERS` explicit list
  - Rationale: cross-origin API controls without wildcard risk.
  - Verify: preflight requests from allowed origin succeed; wildcard use is rejected in prod.

### Abuse Controls and Request Size Limits
- DRF throttles:
  - `DRF_THROTTLE_ANON`
  - `DRF_THROTTLE_USER`
- Middleware rate limits:
  - `RATE_LIMIT_LOGIN`, `RATE_LIMIT_PASSWORD_RESET`, etc.
- Request-size controls:
  - `DATA_UPLOAD_MAX_MEMORY_SIZE`
  - `FILE_UPLOAD_MAX_MEMORY_SIZE`
  - `DATA_UPLOAD_MAX_NUMBER_FIELDS`
  - Nginx `client_max_body_size` in `nginx/conf.d/nbms.conf`
  - Rationale: brute-force and payload-abuse mitigation.
  - Verify: repeated login/API attempts eventually return `429`.

### Database and Pooling
- `DATABASE_URL`
- `DB_CONN_MAX_AGE` (default `600`)
- `DB_DISABLE_SERVER_SIDE_CURSORS` (PgBouncer transaction mode support)
  - Rationale: stable connection reuse and pooling compatibility.
  - Verify: inspect effective settings and DB behavior under load.

### Observability and Error Monitoring
- Logging:
  - `DJANGO_LOG_LEVEL`
  - `DJANGO_LOG_JSON`
- Sentry (optional, disabled unless DSN set):
  - `SENTRY_DSN`
  - `SENTRY_ENVIRONMENT`
  - `SENTRY_TRACES_SAMPLE_RATE`
  - `SENTRY_PROFILES_SAMPLE_RATE`
  - `SENTRY_SEND_DEFAULT_PII`
  - `SENTRY_RELEASE`
  - Rationale: structured diagnostics with controlled PII.
  - Verify: logs include request metadata; no cleartext passwords/tokens.

### Health and Readiness
- `HEALTHCHECK_SKIP_MIGRATION_CHECK` (optional temporary override)
- Endpoints:
  - `/healthz/`
  - `/readyz/`
  - Rationale: orchestration-safe liveness/readiness signals.
  - Verify: `curl -fsS http://<host>/healthz/` and `/readyz/`.

## Deploy-Time Control Command
Use:
```bash
python manage.py predeploy_check
```
This validates required env vars, runs `check --deploy`, and runs `migrate --check`.
