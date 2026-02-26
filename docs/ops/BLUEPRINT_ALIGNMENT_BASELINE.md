# Blueprint Alignment Baseline

- Date/time: 2026-02-25 17:02:23 +02:00
- Branch: `chore/align-blueprint-2026Q1`
- Scope: Step 0 baseline checks before alignment edits

## Baseline Status

- Backend tests (`PYTHONPATH=src pytest -q`): PASS
  - Result: `417 passed, 1 skipped, 16 warnings in 145.19s`
  - Risk note: warnings include Django 6.0 deprecations (`CheckConstraint.check`, `URLField.assume_scheme`).
- Frontend unit tests (`npm run test -- --watch=false --browsers=ChromeHeadless`): PASS
  - Result: `11 passed files, 12 passed tests`
  - Note: npm warns that forwarded `--watch`/`--browsers` flags are unknown for this script wrapper.
- E2E smoke (`npm run e2e`): FAIL (environmental)
  - Failure: bootstrap step cannot reach Docker engine pipe (`//./pipe/dockerDesktopLinuxEngine` not found).
- Docker build (`docker compose -f docker-compose.prod.yml build`): FAIL (environmental)
  - Failure: Docker daemon unavailable (`dockerDesktopLinuxEngine` pipe not found).

## High-Risk Findings

- Local environment cannot run Docker-dependent checks right now, which blocks:
  - Playwright bootstrap relying on backend container lifecycle.
  - Image build verification.
- Backend and frontend unit coverage are currently healthy, so most regressions remain detectable while Docker is unavailable.
