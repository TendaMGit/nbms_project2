$ErrorActionPreference = "Stop"
$env:COMPOSE_PROJECT_NAME = "nbms_dev"

docker compose --profile superset -f compose.yml -f docker-compose.superset.yml stop superset superset_worker superset_beat superset_redis superset_db
