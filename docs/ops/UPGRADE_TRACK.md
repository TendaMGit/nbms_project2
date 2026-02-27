# Controlled Upgrade Track (2026 Q1 Redo)

## Scope
This branch applies low-risk and medium-risk dependency updates only, in a controlled sequence with full verification after each upgrade group.

## Included Upgrade Classes
- Low risk:
  - `psycopg2-binary` patch
  - `drf-spectacular` patch
  - `python-dotenv` patch
  - `pip-tools` dev bump
  - Safe GitHub Actions version bumps where compatible
- Frontend patch set:
  - Angular 21.1.3 -> 21.2.0 coordinated update
- Medium risk (one package per commit):
  - `sentry-sdk`
  - `django-filter`
  - `dj-database-url`
  - `phonenumbers`

## Explicit Deferrals (High Risk)
The following are deferred and **not** part of this branch:
- Python base image `3.14-slim`
- Redis `5.x -> 7.x`
- `django-guardian` `2.4.0 -> 3.3.0`

## Verification Gates
Run for low-risk set and for each medium-risk package bump:

```bash
python manage.py check
pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend run e2e
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
curl http://localhost:8081
curl http://localhost:8000/api/system/health
```

## Failure Policy
If a dependency bump causes regressions:
1. Revert that bump immediately.
2. Record failure details under "Blocked upgrades" in this document.
3. Continue with remaining safe updates.

## Blocked Upgrades
- None yet.
