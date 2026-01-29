#!/usr/bin/env bash
set -euo pipefail

GEO=false
if [ "${1:-}" = "--include-geoserver" ]; then
  GEO=true
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker does not appear to be running. Start Docker and try again." >&2
  exit 1
fi

scripts/verify_env.sh .env docker/docker-compose.yml

services=(postgis redis minio minio-init)
if [ "$GEO" = "true" ]; then
  services+=(geoserver)
fi

echo "Starting infrastructure services: ${services[*]}"

docker compose -f docker/docker-compose.yml --env-file .env up -d "${services[@]}"
