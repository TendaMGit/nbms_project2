# Performance notes

## Query optimizations

- National target and indicator list/detail views now use `select_related` for
  `organisation` and `created_by`, reducing N+1 queries when rendering lists.
- Indicator queries also `select_related` the parent `national_target`.

## Indexes

Indexes added to support common filters used by ABAC and governance checks:
- `status`
- `sensitivity`
- `organisation`
- `created_by`

These indexes exist on both `NationalTarget` and `Indicator` and support frequent
filters in list/detail views and authorization checks.

## Background tasks

No Celery wiring is added yet. If exports or ingestion become heavy, introduce
Celery + Redis in Phase 6 with a focused task queue and monitoring.
