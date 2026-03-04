$ErrorActionPreference = "Stop"
$env:COMPOSE_PROJECT_NAME = "nbms_dev"

docker compose --profile superset -f compose.yml -f docker-compose.superset.yml exec -T superset /app/.venv/bin/python /app/docker/bootstrap_nbms_db.py
