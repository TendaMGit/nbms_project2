# Upgrade Track 2026Q1

Branch: `chore/upgrade-track-2026Q1`
Date: 2026-02-26

## Purpose

Isolate and validate high-risk Dependabot updates before any merge to `main`.

Covered PRs:
- #34 `python:3.12-slim` -> `python:3.14-slim` (HIGH)
- #48 `django-guardian` 2.4.0 -> 3.3.0 (HIGH)
- #50 `redis` 5.0.8 -> 7.2.1 (HIGH)

## Why Isolated

- Python 3.14 image bump is a runtime-major jump with dependency compatibility risk.
- `django-guardian` major jump can change object-level permission behavior and access control decisions.
- Redis major bump can affect container behavior and integration assumptions.

## Execution Plan

1. Recreate each change from archived Dependabot heads on this branch (one change at a time).
2. Run full verification after each step:
   - `python manage.py check`
   - `pytest -q`
   - `npm --prefix frontend ci`
   - `npm --prefix frontend run build`
   - `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless`
   - `npm --prefix frontend run e2e`
   - `docker compose --profile minimal up -d --build`
   - `docker compose -f docker-compose.prod.yml up -d --build`
   - Smoke endpoints: `/`, `/api/system/health`
3. Record findings and regressions per step in this file.
4. Open one consolidation PR only after all checks pass.

## Rollback Plan

- Revert the specific upgrade commit if regressions appear.
- Keep unaffected upgrades in track branch for continued testing.
- Do not merge partial high-risk upgrades into `main`.

## Current Status

- Track branch created.
- High-risk PRs remain closed on `main` pending isolated validation.
