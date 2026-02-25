# Queue and Flower Runbook

Date: 2026-02-25

## Current decision

NBMS does not currently run Celery workers in this branch.
Background execution is handled through programme run orchestration inside the existing Django service.

Because Celery is not active, Flower is intentionally not deployed.

## Revisit criteria

Introduce Celery + Flower only when all are true:
1. At least 3 distinct long-running jobs require true async isolation.
2. Retry/backoff and queue separation are required operationally.
3. Worker autoscaling or dedicated queue monitoring is needed.

Potential candidates:
- heavy report export batches
- large dossier generation jobs
- partner integration sync bursts

Until then, rely on:
- `background_jobs_total` metrics
- programme run status endpoints
- system health operational panels
