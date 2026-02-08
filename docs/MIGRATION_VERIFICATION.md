# Migration Verification

This repository uses a Docker-based migration verification path as the canonical check.

## Canonical Command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_migrations.ps1
```

## What It Verifies

1. Build verification image (`docker/verify/Dockerfile`).
2. Bring up isolated PostGIS verify stack (`docker-compose.verify.yml`).
3. Run:
   - `python manage.py migrate`
   - `python manage.py check`
   - `pytest -q`
   - `python manage.py verify_post_migration`
4. Tear down verify stack.

## Policy

- Any schema-affecting PR must pass this flow.
- Spatial migrations must be verified in a GIS-capable container path (PostGIS + GDAL/GEOS available).
- Windows non-GIS smoke checks are allowed to skip spatial migration execution but must not break baseline app startup/tests.
