# Blueprint Verification Outputs

Date: 2026-02-25  
Branch: `chore/align-blueprint-2026Q1`

## Backend

Command:
```powershell
$env:PYTHONPATH='src'; pytest -q
```
Result: PASS
- `422 passed, 1 skipped, 16 warnings`

Command:
```powershell
$env:PYTHONPATH='src'; python manage.py check --settings=config.settings.dev
```
Result: PASS
- `System check identified no issues (0 silenced).`

Command:
```powershell
$env:PYTHONPATH='src'
$env:SECRET_KEY='dummy-secret-key-for-checks'
$env:ALLOWED_HOSTS='localhost,127.0.0.1'
$env:CSRF_TRUSTED_ORIGINS='http://localhost,http://127.0.0.1'
$env:DATABASE_URL='sqlite:///db.prod.check.sqlite3'
python manage.py check --deploy --settings=config.settings.prod
```
Result: PASS (warnings only)
- Existing `drf_spectacular.W001/W002` and security warnings remain.

Command:
```powershell
$env:PYTHONPATH='src'
$env:SECRET_KEY='dummy-secret-key-for-checks'
$env:ALLOWED_HOSTS='localhost,127.0.0.1'
$env:CSRF_TRUSTED_ORIGINS='http://localhost,http://127.0.0.1'
$env:DATABASE_URL='sqlite:///db.prod.check.sqlite3'
python manage.py migrate --settings=config.settings.prod --noinput
python manage.py predeploy_check --settings=config.settings.prod
```
Result: PASS
- `Pre-deploy checks passed.`

## Frontend

Command:
```powershell
npm --prefix frontend run build
```
Result: PASS
- Build completed; Angular warnings only (CommonJS + template nullish note).

Command:
```powershell
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
```
Result: PASS
- `11 passed` files, `12 passed` tests.

Command:
```powershell
npm --prefix frontend run e2e
```
Result: PASS
- `3 passed` Playwright smoke tests.

## Docker

Command:
```powershell
docker compose -f docker-compose.prod.yml config
```
Result: PASS
- Compose file rendered successfully with app/db/redis/nginx services.

Command:
```powershell
docker build -f Dockerfile -t nbms-prod-local-check .
```
Result: PASS
- Production image built successfully after adding Cairo build/runtime dependencies.

## Notes

- E2E bootstrap updates runtime demo users and writes a session key file under `frontend/e2e/`; this file remains ignored and untracked.
- Existing deploy warnings are pre-existing schema/docs generation items and are not introduced by this alignment work.
