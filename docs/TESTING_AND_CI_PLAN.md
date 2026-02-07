# TESTING_AND_CI_PLAN

## Current Status (2026-02-07)

### Backend
- Command:
  - `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q`
- Result:
  - `352 passed` (full suite)
  - includes new API coverage for:
    - `src/nbms_app/tests/test_api_programme_ops.py`
    - `src/nbms_app/tests/test_programme_ops_commands.py`
    - `src/nbms_app/tests/test_api_birdie_integration.py`
    - `src/nbms_app/tests/test_api_report_products.py`
    - `src/nbms_app/tests/test_api_template_packs.py`

### Frontend
- Build:
  - `cd frontend && npm run build`
- Unit tests:
  - `cd frontend && npm run test`
- Result:
  - build passes
  - `8 passed` (Angular app + NR7/system-health/programme-ops/template-pack/birdie/report-product component tests)
  - Playwright smoke (`npm run e2e`) passes

### Docker smoke
- Command:
  - `docker compose --profile minimal up -d --build`
- Verified:
  - backend health: `http://127.0.0.1:8000/health/`
  - frontend proxy health: `http://127.0.0.1:8081/health/`
- API surface through proxy: `http://127.0.0.1:8081/api/help/sections`
  - Angular route availability check: `http://127.0.0.1:8081/programmes`

## CI Pipeline (implemented)
File: `.github/workflows/ci.yml`

- `frontend-build`
  - install frontend dependencies
  - Angular build + unit tests
- `quality-fast`
  - pip check
  - syntax compile
  - `manage.py check`
  - migrations drift check
- `tests-linux-full`
  - PostGIS-backed full backend pytest suite
- `tests-windows-smoke`
  - Windows smoke checks for backend/test tooling
- `security-baseline`
  - Bandit SAST (`bandit -lll -ii`)
  - dependency audit
  - Trivy filesystem scan
  - Trivy backend container image scan
  - gitleaks secret scan
  - `manage.py check --deploy`
- `docker-minimal-smoke`
  - build/start minimal compose profile
  - verify backend and frontend availability
  - run Playwright smoke through docker-served frontend
  - teardown stack

## Testing Gaps
- Expand frontend test surface beyond shell-level assertions:
  - dashboard data rendering
  - indicator explorer filters
  - map viewer interaction behavior
- Add integration tests for indicator CSV import path exposed via API (future increment).
- Add performance tests for spatial feature query bounding and pagination.
- Add Semgrep ruleset on top of Bandit for deeper framework-level checks.
- Expand Playwright from smoke coverage to authenticated end-to-end flows (dashboard, map interactions, NR7 builder saves).

## Minimal Contributor Test Plan
1. Backend: `pytest -q`
2. Frontend: `cd frontend && npm run build && npm run test && npm run e2e`
3. Docker smoke: `docker compose --profile minimal up -d --build`
4. Health checks:
   - `http://127.0.0.1:8000/health/`
   - `http://127.0.0.1:8081/health/`
