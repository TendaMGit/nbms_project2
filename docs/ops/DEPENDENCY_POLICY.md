# Dependency Policy

Date: 2026-02-25

## Policy

NBMS uses deterministic dependency inputs for both backend and frontend:

- Python:
  - Source inputs: `requirements.in`, `requirements-dev.in`
  - Locked install files: `requirements.txt`, `requirements-dev.txt`
  - Tooling: `pip-tools` (available in dev dependencies)
- Frontend:
  - Source + lock: `frontend/package.json` + `frontend/package-lock.json`
  - Install command in CI: `npm ci`

## Update workflow

1. Edit `requirements.in` (or `requirements-dev.in`) only.
2. Re-compile lock files:
   ```bash
   pip-compile requirements.in --output-file requirements.txt
   pip-compile requirements-dev.in --output-file requirements-dev.txt
   ```
3. Re-run checks:
   - `python manage.py check`
   - `pytest -q`
   - `pip-audit`

## Security baseline

- `pip-audit` is part of CI baseline.
- `bandit` is part of CI baseline.
- Exceptions must be documented in `docs/security/SECURITY_EXCEPTIONS.md` with an expiry date.

## Install completeness

Always install with:
```bash
pip install -r requirements-dev.txt
npm --prefix frontend ci
```

Avoid ad-hoc `pip install <package>` without recording it in requirements files.
