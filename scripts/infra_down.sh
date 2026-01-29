#!/usr/bin/env bash
set -euo pipefail

VOLUMES=false
if [ "${1:-}" = "--volumes" ]; then
  VOLUMES=true
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker does not appear to be running. Start Docker and try again." >&2
  exit 1
fi

scripts/verify_env.sh .env docker/docker-compose.yml

echo "Stopping infrastructure services..."
if [ "$VOLUMES" = "true" ]; then
  docker compose -f docker/docker-compose.yml --env-file .env down -v
else
  docker compose -f docker/docker-compose.yml --env-file .env down
fi
