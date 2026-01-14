# NBMS Project 2 (Baseline)

Clean, portable baseline for the NBMS platform (PostGIS + MinIO + GeoServer).

## Clean slate on the same server (Docker)

1) Copy the environment file and fill in credentials:

```
copy .env.example .env
```

2) Start infra services:

```
docker compose -f docker/docker-compose.yml up -d postgis redis minio geoserver
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
python manage.py runserver
```

4) Run tests (non-interactive):

```
scripts/test.sh
```

## GeoServer

- See `docs/infra/geoserver.md` for workspace and datastore setup.
- Optional: `scripts/geoserver_bootstrap.sh` will create a workspace and PostGIS datastore.

## Settings

- Dev settings: `config.settings.dev`
- Test settings: `config.settings.test`
- Prod settings: `config.settings.prod`

