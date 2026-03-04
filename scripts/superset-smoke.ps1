if (-not $env:COMPOSE_PROJECT_NAME) {
  $env:COMPOSE_PROJECT_NAME = "nbms_dev"
}

Write-Host "Running analytics health check..."
docker compose exec backend python manage.py debug_analytics_health
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Checking analytics fact row counts via psql..."
docker compose exec postgis sh -lc 'psql -U "$POSTGRES_USER" -d "$NBMS_DB_NAME" -tA -F "," -c "select ''fact_indicator_observation_rows'' as metric, count(*) as row_count from analytics.fact_indicator_observation union all select ''dim_indicator_rows'' as metric, count(*) as row_count from analytics.dim_indicator;"'
exit $LASTEXITCODE
