# NBMS Project 2 (Baseline)

Clean, portable baseline for the NBMS platform (PostGIS + MinIO + GeoServer).

This repo is Windows-first. PowerShell scripts live in `scripts/` alongside Bash versions.

## Prereqs

- Python 3.12 (or 3.11)
- Docker Desktop
- PowerShell 5+ (or PowerShell 7+)

## Windows quickstart (PowerShell)

1) Copy the environment file and fill in credentials:

```
Copy-Item .env.example .env
```

Cmd equivalent:

```
copy .env.example .env
```

2) Start infra services (choose a mode):

Minimal stack (PostGIS + Redis + MinIO):

```
docker compose -f docker/docker-compose.yml up -d postgis redis minio minio-init
```

Full stack (includes GeoServer):

```
docker compose -f docker/docker-compose.yml up -d postgis redis minio minio-init geoserver
```

3) Bootstrap the app (installs deps + migrate):

```
.\scripts\bootstrap.ps1
```

If PowerShell blocks script execution in this shell:

```
Set-ExecutionPolicy -Scope Process Bypass
```

4) Run the server:

```
python manage.py runserver
```

5) Run tests (pytest):

```
.\scripts\test.ps1
```

Ensure the Docker services are running before tests (PostGIS is required).

## Reset databases (PowerShell)

```
$env:CONFIRM_DROP = "YES"
.\scripts\reset_db.ps1
```

To reset against a local Postgres instead of Docker:

```
$env:USE_DOCKER = "0"
```

## Git Bash / macOS / Linux

Bootstrap:

```
./scripts/bootstrap.sh
```

Tests:

```
./scripts/test.sh
```

Reset databases:

```
CONFIRM_DROP=YES scripts/reset_db.sh
```

## Health checks

- App: `http://localhost:8000/health/`
- Storage (when `USE_S3=1`): `http://localhost:8000/health/storage/`

## GeoServer

- See `docs/infra/geoserver.md` for workspace and datastore setup.
- Optional: `scripts/geoserver_bootstrap.sh` will create a workspace and PostGIS datastore.

## Environment notes

- Never commit `.env` (only `.env.example`).
- `POSTGRES_PASSWORD` is the Postgres superuser password used by init/reset scripts.
- `NBMS_DB_PASSWORD` is the app database user password.
- `USE_S3=1` enables MinIO-backed media storage; `USE_S3=0` uses local filesystem.
- `ENABLE_GEOSERVER=1` enables GeoServer checks in scripts.
- Configure `EMAIL_*` vars to enable password reset emails in non-dev environments.

## Settings

- Dev settings: `config.settings.dev`
- Test settings: `config.settings.test`
- Prod settings: `config.settings.prod`

## Branching + PR discipline

- Always branch from `main`.
- Keep commits small and scoped.
- Tests must pass before merging.
- Model changes require migrations.
