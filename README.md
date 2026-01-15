# NBMS Project 2 (Baseline)

Clean, portable baseline for the NBMS platform (PostGIS + MinIO + GeoServer).

## Clean slate on the same server (Docker)

1) Copy the environment file and fill in credentials:

```
copy .env.example .env
```

2) Start infra services (choose a mode):

A) Minimal stack (PostGIS + Redis + MinIO):

```
docker compose -f docker/docker-compose.yml up -d postgis redis minio minio-init
```

B) Full stack (includes GeoServer):

```
docker compose -f docker/docker-compose.yml up -d postgis redis minio minio-init geoserver
```

3) Bootstrap the app (installs deps + migrate):

```
scripts/bootstrap.sh
```

4) Reset databases (only when you need a clean slate):

```
CONFIRM_DROP=YES scripts/reset_db.sh
```

Use `USE_DOCKER=0` to run the reset against a local Postgres (requires `psql`).

5) Run the server:

```
python manage.py runserver
```

## Quickstart (local, no Docker)

1) Create a virtual environment and install deps:

```
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

2) Create your `.env` file from the example and fill in credentials:

```
copy .env.example .env
```

3) Run migrations and start the server:

```
python manage.py migrate
python manage.py bootstrap_roles
python manage.py seed_report_templates
python manage.py seed_validation_rules
python manage.py runserver
```

4) Run tests (non-interactive):

```
scripts/test.sh
```

Notes:
- Default test script uses `--keepdb` to avoid prompts on re-runs.
- For CI, set `CI=1` (uses `--noinput`).
- To drop only the test DB: `CONFIRM_DROP_TEST=YES scripts/drop_test_db.sh`.

## GeoServer

- See `docs/infra/geoserver.md` for workspace and datastore setup.
- Optional: `scripts/geoserver_bootstrap.sh` will create a workspace and PostGIS datastore.

## Environment notes

- `POSTGRES_PASSWORD` is the Postgres superuser password used by init/reset scripts.
- `NBMS_DB_PASSWORD` is the app database user password.
- `USE_S3=1` enables MinIO-backed media storage; `USE_S3=0` uses local filesystem.
- `ENABLE_GEOSERVER=1` enables GeoServer checks in scripts.
- Configure `EMAIL_*` vars to enable password reset emails in non-dev environments.

## Settings

- Dev settings: `config.settings.dev`
- Test settings: `config.settings.test`
- Prod settings: `config.settings.prod`

## Reporting

- Manager Report Pack preview: `/reporting/instances/<uuid>/report-pack/` (staff-only).
- Use the browser print dialog to save a PDF (server-side PDF generation is not implemented yet).

## Rulesets

ValidationRuleSet controls which sections and metadata fields are required for readiness checks.
The readiness service uses the active ruleset (by default `7NR_DEFAULT`).

Seed defaults:

```
python manage.py seed_validation_rules
```

You can override the rules in the admin UI, but keep only one active ruleset unless you
intentionally want multiple active configurations.

