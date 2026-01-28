# Migration Verification (Canonical)

This repo uses a Docker-based verification environment to ensure migration 0026 runs end-to-end with PostGIS + GDAL.

## Windows (Docker Desktop)

1) Copy the verification env file:

```
copy .env.verify.example .env.verify
```

2) Run the verification script:

```
scripts\verify_migrations.ps1
```

Optional: keep containers running for inspection:

```
scripts\verify_migrations.ps1 -KeepAlive
```

## Linux/macOS (Docker)

```
cp .env.verify.example .env.verify

docker compose -f docker-compose.verify.yml --env-file .env.verify run --rm app ./scripts/verify_migrations.sh
```

## What the script does

- Starts PostGIS (with GDAL available in the app container)
- Drops and recreates a clean DB
- Runs `python manage.py migrate`
- Runs `python manage.py check`
- Runs `pytest -q`
- Runs `python manage.py verify_post_migration`

Expected output includes:
- `Post-migration verification passed.`

## CI Gate (Linux)

Workflow: `.github/workflows/migration-verify.yml`

To enforce this as a required check, enable branch protection on `main` and require the workflow name:
- **Migration Verification**

## Local GDAL limitation (historical)

Attempts to run migrations locally on Windows without GDAL fail during Django startup:

`OSError: [WinError 127] The specified procedure could not be found` (GDAL binding)

Use the Docker-based path above to avoid local GDAL dependencies.
