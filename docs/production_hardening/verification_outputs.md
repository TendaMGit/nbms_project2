# Verification Outputs

Generated: 2026-02-24

## 1) Python test suite
Command:
```bash
PYTHONPATH=src pytest -q
```
Result: PASS
Trimmed output:
```text
417 passed, 1 skipped, 16 warnings in 141.63s (0:02:21)
```

## 2) Django checks (dev)
Command:
```bash
PYTHONPATH=src python manage.py check --settings=config.settings.dev
```
Result: PASS
Trimmed output:
```text
System check identified no issues (0 silenced).
```

## 3) Django deploy checks (prod settings with dummy env)
Command:
```bash
PYTHONPATH=src DJANGO_READ_DOT_ENV_FILE=0 \
DJANGO_SECRET_KEY='CI_SECURITY_SECRET_KEY_1234567890_ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
DATABASE_URL='sqlite:///tmp_prod_check.sqlite3' \
DJANGO_ALLOWED_HOSTS='example.org' \
DJANGO_CSRF_TRUSTED_ORIGINS='https://example.org' \
python manage.py check --deploy --settings=config.settings.prod
```
Result: PASS (with warnings)
Trimmed output:
```text
System check identified 91 issues (0 silenced).
```
Notes:
- Warnings are primarily DRF Spectacular schema warnings and `security.W021` (`SECURE_HSTS_PRELOAD` not set true), which is intentionally env-toggle controlled.

## 4) Predeploy command (prod settings with dummy env)
Command:
```bash
PYTHONPATH=src DJANGO_READ_DOT_ENV_FILE=0 \
DJANGO_SECRET_KEY='CI_SECURITY_SECRET_KEY_1234567890_ABCDEFGHIJKLMNOPQRSTUVWXYZ' \
DATABASE_URL='sqlite:///tmp_predeploy_check.sqlite3' \
DJANGO_ALLOWED_HOSTS='example.org' \
DJANGO_CSRF_TRUSTED_ORIGINS='https://example.org' \
python manage.py predeploy_check --settings=config.settings.prod --skip-migrate-check
```
Result: PASS (with warnings from `check --deploy`)
Trimmed output:
```text
Running django deploy checks...
Pre-deploy checks passed.
```

## 5) Docker compose production config validation
Command:
```bash
docker compose -f docker-compose.prod.yml config
```
Result: PASS
Trimmed output:
```text
name: nbms_project2
services:
  app:
    build:
      dockerfile: Dockerfile
  db:
    image: postgis/postgis:16-3.4
  nginx:
    image: nginx:1.27-alpine
  redis:
    image: redis:7-alpine
```

## 6) Dockerfile reference validation
Command:
```bash
# PowerShell path validation of Dockerfile COPY sources
```
Result: PASS
Trimmed output:
```text
Dockerfile COPY path check passed.
```

## 7) Additional branch safety checks
Command:
```bash
git ls-files | Select-String -Pattern "(\.env$|\.env\.)"
```
Result: PASS (no tracked `.env` secrets file; only templates)
Trimmed output:
```text
.env.example
.env.verify.example
```

Command:
```bash
git ls-files size scan (top 10 largest tracked files)
```
Result: PASS (no newly introduced suspicious runtime artifacts)
Top entries:
```text
608126 docs/external/cop-16-dec-31-en.pdf
454965 docs/external/gbf-headline-A-1.html
313179 frontend/package-lock.json
```

## Environment limitation
- Docker daemon runtime bring-up (`docker compose ... up`) could not be re-verified in this session if daemon/engine is unavailable on host.
- Syntax/config validation and path checks passed.
