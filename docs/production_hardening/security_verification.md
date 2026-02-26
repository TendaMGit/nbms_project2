# Security Verification Guide

## Scope
Run these checks after deployment to confirm the production hardening baseline is active.

## 1) Deploy Checks
```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_READ_DOT_ENV_FILE=0 \
DJANGO_SECRET_KEY='...' DATABASE_URL='...' DJANGO_ALLOWED_HOSTS='...' \
DJANGO_CSRF_TRUSTED_ORIGINS='...' python manage.py predeploy_check
```
Expected: `Pre-deploy checks passed.`

## 2) Liveness and Readiness
```bash
curl -fsS http://127.0.0.1/healthz/
curl -fsS http://127.0.0.1/readyz/
```
Expected:
- `/healthz/` -> `{"status":"ok"}`
- `/readyz/` -> `{"status":"ready",...}` when DB + migrations are ready

## 3) Security Headers
```bash
curl -I http://127.0.0.1/healthz/
```
Validate presence of:
- `Content-Security-Policy` (or `Content-Security-Policy-Report-Only`)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`
- `Cross-Origin-Opener-Policy`
- `X-Request-ID`

## 4) Cookie Hardening
Automated verification:
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_security_headers.py
```
This checks:
- session cookie `Secure`, `HttpOnly`, `SameSite`
- CSRF cookie `Secure`, `HttpOnly`, `SameSite`

## 5) Rate Limiting and Abuse Controls
Automated verification:
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_rate_limiting.py
```
Manual smoke test example:
```bash
for i in {1..7}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1/accounts/login/; done
```
Expected: repeated attempts eventually return `429`.

## 6) CORS Guardrails
- Ensure production does not set `CORS_ALLOW_ALL_ORIGINS=true`.
- Validate allowed origins are explicit via `CORS_ALLOWED_ORIGINS`.

Automated prod guardrail check:
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_prod_settings.py
```

## 7) Logging and Redaction
Automated verification:
```bash
PYTHONPATH=src pytest -q src/nbms_app/tests/test_logging_utils.py
```
Checks include:
- structured fields in JSON logs
- request metadata defaults
- password/token redaction behavior

## 8) CI Gate Verification
Ensure CI job `security-baseline` passes with:
- `python manage.py check --deploy`
- `make deploy-check`
- Bandit and pip-audit baseline jobs

## 9) Production Compose Validation
```bash
docker compose -f docker-compose.prod.yml config
```
Expected: successful config render with no schema errors.
