$ErrorActionPreference = "Stop"
$env:COMPOSE_PROJECT_NAME = "nbms_dev"

docker compose --profile superset -f compose.yml -f docker-compose.superset.yml logs -f --tail=200 superset
