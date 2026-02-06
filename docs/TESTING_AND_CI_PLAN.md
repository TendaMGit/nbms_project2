# TESTING_AND_CI_PLAN

## Current Status (2026-02-06)

### Backend
- Command:
  - `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q`
- Result:
  - `324 passed` (full suite)

### Frontend
- Build:
  - `cd frontend && npm run build`
- Unit tests:
  - `cd frontend && npm run test`
- Result:
  - build passes
  - `2 passed` (current Angular shell tests)

### Docker smoke
- Command:
  - `docker compose --profile minimal up -d --build`
- Verified:
  - backend health: `http://127.0.0.1:8000/health/`
  - frontend proxy health: `http://127.0.0.1:8081/health/`
  - API surface through proxy: `http://127.0.0.1:8081/api/help/sections`

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
  - dependency audit
  - gitleaks secret scan
  - `manage.py check --deploy`
- `docker-minimal-smoke`
  - build/start minimal compose profile
  - verify backend and frontend availability
  - teardown stack

## Testing Gaps
- Expand frontend test surface beyond shell-level assertions:
  - dashboard data rendering
  - indicator explorer filters
  - map viewer interaction behavior
- Add integration tests for indicator CSV import path exposed via API (future increment).
- Add performance tests for spatial feature query bounding and pagination.
- Add SAST/static security analyzer stage (Bandit/Semgrep or equivalent) in CI.

## Minimal Contributor Test Plan
1. Backend: `pytest -q`
2. Frontend: `cd frontend && npm run build && npm run test`
3. Docker smoke: `docker compose --profile minimal up -d --build`
4. Health checks:
   - `http://127.0.0.1:8000/health/`
   - `http://127.0.0.1:8081/health/`
