# Dependabot Triage Plan

Date: 2026-02-26
Base branch: `main`
Scope: PRs #31-#54

## Context

All listed Dependabot PRs were previously closed when their branches were cleaned up. Archive tags exist for each head branch (`archive/dependabot/...`). This plan restores only the PRs needed for safe processing and keeps high-risk upgrades out of `main` until isolated verification is complete.

## Risk Groups

### LOW (merge now if CI + minimal docker verification pass)

- #54 `psycopg2-binary` 2.9.10 -> 2.9.11
- #46 `drf-spectacular` 0.28.0 -> 0.29.0
- #45 `python-dotenv` 1.0.1 -> 1.2.1
- #31 `actions/checkout` 4 -> 6
- #32 `actions/setup-python` 5 -> 6
- #33 `github/codeql-action` 3 -> 4
- #35 `aquasecurity/trivy-action` 0.24.0 -> 0.34.1
- #36-#44 Angular 21.1.3 -> 21.2.0 minor bumps

### MEDIUM (merge one-by-one, full local verify + docker smoke)

- #52 `sentry-sdk` 2.20.0 -> 2.53.0
- #51 `django-filter` 24.3 -> 25.2
- #47 `dj-database-url` 2.2.0 -> 3.1.2
- #53 `phonenumbers` 8.13.40 -> 9.0.25

### HIGH (do not merge to `main` now)

- #34 Docker base image `python:3.12-slim` -> `3.14-slim`
- #50 `redis` 5.0.8 -> 7.2.1
- #48 `django-guardian` 2.4.0 -> 3.3.0

## Merge Plan

1. Merge LOW risk PRs first (CI green required).
2. Verify locally after LOW batches:
   - Backend: `python manage.py check`, `pytest -q`
   - Frontend: `npm --prefix frontend ci`, `npm --prefix frontend run build`, `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless`, `npm --prefix frontend run e2e`
   - Docker minimal verify: `docker compose -f docker-compose.prod.yml build --no-cache backend`
3. Merge MEDIUM PRs individually; after each merge run:
   - `pytest -q`
   - frontend build/test/e2e
   - `docker compose -f docker-compose.prod.yml up -d --build`
   - smoke: frontend root and `/api/system/health`
4. Keep HIGH risk PRs out of `main`; use upgrade track:
   - Branch: `chore/upgrade-track-2026Q1`
   - Doc: `docs/ops/UPGRADE_TRACK.md`
   - Validate runtime/dependency compatibility before proposing merge.

## Verification Gate (required for merge)

A PR is mergeable now only when all are true:
- GitHub checks pass.
- Local checks pass for its risk class.
- Minimal docker verification passes.
- Merge method: squash with `--delete-branch`.
