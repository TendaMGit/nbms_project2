$ErrorActionPreference = "Stop"
$env:COMPOSE_PROJECT_NAME = "nbms_dev"

docker compose --profile superset -f compose.yml -f docker-compose.superset.yml up -d superset_db superset_redis
docker compose --profile superset -f compose.yml -f docker-compose.superset.yml up superset_init
docker compose --profile superset -f compose.yml -f docker-compose.superset.yml up -d superset superset_worker superset_beat
