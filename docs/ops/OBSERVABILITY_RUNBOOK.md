# Observability Runbook

Date: 2026-02-25

## Overview

NBMS observability baseline now includes:
- Prometheus metrics (`/metrics/` and staff-gated `/api/system/metrics`)
- Structured request logging (JSON optional)
- Optional Loki + Grafana stack (`docker-compose.observability.yml`)
- Optional OpenTelemetry tracing (feature-flagged)
- Optional Sentry error/perf telemetry (feature-flagged)

## Metrics

Core metrics exposed:
- `http_requests_total{method,route,status}`
- `http_request_latency_seconds` (histogram)
- `export_requests_total{type}`
- `downloads_created_total{record_type}`
- `background_jobs_total{job_type,status}`
- `db_pool_connections{alias}`
- `tile_requests_total{layer}`

Access control:
- `/metrics/`:
  - system admin session OR
  - bearer token via `METRICS_TOKEN`
- `/api/system/metrics`:
  - authenticated staff/system-admin only

Do not expose metrics endpoints publicly without network controls.

## Logs

Runtime logs:
- Structured request logs through `RequestLoggingMiddleware`
- Secret redaction via `SensitiveDataFilter`

Docker logging safety:
- App containers use `json-file` logging with `mode=non-blocking` and bounded buffers.

Loki/Grafana stack:
```bash
docker compose -f compose.yml -f docker-compose.observability.yml --profile minimal --profile observability up -d
```

Grafana:
- URL: `http://localhost:3000`
- Datasources are auto-provisioned (Prometheus + Loki).
- Seed dashboard: `ops/observability/grafana/dashboards/nbms-overview.json`

## Tracing (OpenTelemetry, optional)

Enable tracing with env vars:
- `OTEL_ENABLED=true`
- `OTEL_SERVICE_NAME=nbms-backend`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces`
- `OTEL_EXPORTER_OTLP_HEADERS=` (optional)

If OTEL libs are missing or endpoint is unreachable, startup continues with warning logs.

## Sentry (optional)

Enable with:
- `SENTRY_DSN=<dsn>`
- `SENTRY_TRACES_SAMPLE_RATE=0.05` (recommended production baseline)
- `SENTRY_PROFILES_SAMPLE_RATE=0.0`

For high-volume environments, keep traces sample rate low and tune per release.

## System Health Page

`/system/health` now shows:
- service checks (DB/storage/cache)
- observability toggles (metrics/logs/tracing/sentry)
- download backlog
- export failures in last 24h

## Operational checks

```bash
curl -H "Authorization: Bearer $METRICS_TOKEN" http://127.0.0.1:8000/metrics/
curl -b "sessionid=<staff_session>" http://127.0.0.1:8000/api/system/metrics
curl http://127.0.0.1:8000/api/system/health
```
