# NBMS Project 2 (Baseline)

Clean, portable baseline for the NBMS platform (PostGIS + MinIO + GeoServer).

## Purpose and scope

NBMS Project 2 is a manager-ready prototype for biodiversity reporting workflows,
including governance, consent checks, and instance-scoped approvals.

Blueprint boundary (authoritative operating stance):
- NBMS is a governed registry, ingestion, validation, publication, and reporting platform.
- Indicator computation pipelines remain contributor-owned and run outside NBMS.
- NBMS stores approved releases and exposes search, exports, readiness, and reporting outputs.
- Governance is minimal: ITSC approves methods, and Data Steward review is conditional for flagged sensitivity/licence/IPLC cases.
- Delivery is framed as `Phase 1 - National MVP (Reporting + Interoperability + Scale Path)` with backlog tiers inside Phase 1.

## Feature summary

- Auth and staff management UI (no Django admin needed for day-to-day)
- ABAC and object-level access controls
- Workflow transitions with audit trail and notifications
- Reporting cycles and instances with freeze and approvals
- Consent gating for IPLC-sensitive content
- Export packages with instance-scoped approvals
- ORT NR7 v2 export (gated) at `/exports/instances/<uuid>/ort-nr7-v2.json`
- Ramsar/CITES/CMS template-pack runtime (Ramsar includes QA + PDF export)
- BIRDIE connector ingest with bronze/silver/gold lineage persistence
- Report product framework for NBA/GMO/Invasive shells (HTML/PDF)
- Manager report pack preview (HTML)
- Reference catalog UI for programmes, datasets, methodologies, agreements, and sensitivity classes

## Authoritative runbook

See `docs/ops/STATE_OF_REPO.md` for the authoritative Windows-first runbook, posture, and repo state.

## Demo flow

1) Create a reporting cycle and reporting instance.
2) Seed section templates and validation rules.
3) Capture Section I to V narrative content.
4) Create targets, indicators, evidence, and catalog datasets (with programme/method/indicator links).
5) Approve items for the instance and resolve consent blockers.
6) Review the manager report pack preview.
7) Release an export package once blockers are cleared.

## Quickstart (Docker-first) - Primary

1) Create `.env` from example and set required secrets:

```
copy .env.example .env
```

Required for Docker compose:
- `POSTGRES_PASSWORD`
- `NBMS_DB_PASSWORD`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `GEOSERVER_PASSWORD` (only required for `spatial` profile)

2) Start deterministic infrastructure:

A) Minimal profile:

```
docker compose --profile minimal up -d --build
```

B) Full profile (minimal + GeoServer):

```
docker compose --profile full up -d --build
```

C) Spatial profile (minimal + GeoServer, spatial-focused):

```
docker compose --profile spatial up -d --build
```

3) Run backend bootstrap/migrations:

```
scripts\bootstrap.ps1
python manage.py bootstrap_roles
python manage.py seed_reporting_defaults
python manage.py seed_mea_template_packs
python manage.py seed_gbf_indicators
python manage.py seed_birdie_integration
python manage.py seed_report_products
```

4) Start backend and run smoke checks:

```
python manage.py runserver
scripts\smoke.ps1
```

Docker-first URLs:
- Angular app + reverse proxy: `http://localhost:8081/`
- Backend direct: `http://localhost:8000/`
- Health through frontend proxy: `http://localhost:8081/health/`
- BIRDIE dashboard route: `http://localhost:8081/programmes/birdie`
- Report products route: `http://localhost:8081/report-products`

## Quickstart (Windows no-Docker fallback)

1) Create a virtual environment and install deps:

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2) Create your `.env` file from the example and fill in credentials:

```
copy .env.example .env
```

3) Set Windows-first environment variables (PowerShell):

```
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:DJANGO_DEBUG='true'
$env:ENABLE_GIS='false'
$env:DATABASE_URL='postgresql://nbms_user:YOUR_PASSWORD@localhost:5432/nbms_project2_db'
$env:USE_S3='0'
$env:USE_REDIS='0'
```

`ENABLE_GIS=false` avoids the GDAL/GEOS dependency on Windows.
Redis is optional for local login. Set `USE_REDIS=1` and `REDIS_URL=redis://localhost:6379/0`
only if you are running Redis.

4) Run migrations and start the server:

```
python manage.py migrate
python manage.py bootstrap_roles
python manage.py seed_report_templates
python manage.py seed_validation_rules
# or run both at once:
python manage.py seed_reporting_defaults
python manage.py runserver
```

Deterministic setup shortcut (PowerShell):

```
scripts\bootstrap.ps1
python manage.py bootstrap_roles
python manage.py seed_reporting_defaults
```

5) Smoke check (PowerShell):

```
Invoke-WebRequest http://127.0.0.1:8000/health/ | Select-Object -Expand Content
Invoke-WebRequest http://127.0.0.1:8000/health/storage/ | Select-Object -Expand Content
# or
scripts\smoke.ps1
```

Expected responses (with `USE_S3=0`):
- `/health/` -> `{ "status": "ok" }`
- `/health/storage/` -> `{ "status": "disabled", "detail": "USE_S3=0" }`

6) Run tests (PowerShell):

```
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
$env:PYTHONPATH="$PWD\src"
pytest -q
# or
scripts\test.ps1
```

Notes:
- Default test script (`scripts/test.sh`, bash) uses `--keepdb` to avoid prompts on re-runs.
- PowerShell parity script (`scripts/test.ps1`) follows the same `--keepdb` default.
- For CI, set `CI=1` (uses `--noinput`).
- PowerShell users should prefer the `pytest -q` command above.
- To drop only the test DB: `CONFIRM_DROP_TEST=YES scripts/drop_test_db.sh`.
  Use this if `--keepdb` hits schema drift or test DB mismatch errors.
The helper drops ONLY the configured test DB and refuses to run if it matches the main DB.

## Docker Profiles

Minimal stack (PostGIS + Redis + MinIO):

```
docker compose --profile minimal up -d --build
```

Full stack (minimal + GeoServer):

```
docker compose --profile full up -d --build
```

Spatial stack (minimal + GeoServer):

```
docker compose --profile spatial up -d --build
```

Legacy infra-only compose file remains available at `docker/docker-compose.yml` for service-only startup.

Reset databases (only when you need a clean slate):

```
CONFIRM_DROP=YES scripts/reset_db.sh
```

Use `USE_DOCKER=0` to run the reset against a local Postgres (requires `psql`).

Run the server:

```
python manage.py runserver
```

## Migration verification (Docker)

Windows (Docker Desktop):

```
copy .env.verify.example .env.verify
scripts\\verify_migrations.ps1
```

Linux/macOS:

```
cp .env.verify.example .env.verify
docker compose -f docker-compose.verify.yml --env-file .env.verify run --rm app ./scripts/verify_migrations.sh
```

This path provides PostGIS + GDAL and runs migrations, checks, tests, and post-migration assertions.

## Manual smoke pass

Setup order:
1) python manage.py migrate
2) python manage.py bootstrap_roles
3) python manage.py seed_report_templates
4) python manage.py seed_validation_rules (or seed_reporting_defaults)
5) python manage.py runserver

Staff login expected behavior:
- Staff user can access management and reporting pages.
- Non-staff is blocked from staff-only pages.

Key URLs to test:
- /
- /manage/users/
- /manage/organisations/
- /datasets/
- /catalog/monitoring-programmes/
- /catalog/methodologies/
- /catalog/methodology-versions/
- /catalog/data-agreements/
- /catalog/sensitivity-classes/
- /frameworks/
- /framework-targets/
- /framework-indicators/
- /reporting/cycles/
- /reporting/instances/<uuid>/
- /reporting/instances/<uuid>/sections/
- /reporting/instances/<uuid>/approvals/
- /reporting/instances/<uuid>/consent/
- /reporting/instances/<uuid>/report-pack/
- /exports/

Confirm export blockers:
- Missing required sections should block export when EXPORT_REQUIRE_SECTIONS=1.
- Missing consent for IPLC-sensitive approved items should block export.
- When EXPORT_REQUIRE_READINESS=1, export/release is blocked if catalog readiness is not satisfied.

ABAC quick check:
- Create a restricted item in Org A and verify it is not visible to a user in Org B.

## GeoServer

- See `docs/infra/geoserver.md` for workspace and datastore setup.
- Optional: `scripts/geoserver_bootstrap.sh` will create a workspace and PostGIS datastore.

## Environment notes

- `POSTGRES_PASSWORD` is the Postgres superuser password used by init/reset scripts.
- `NBMS_DB_PASSWORD` is the app database user password.
- `USE_S3=1` enables MinIO-backed media storage; `USE_S3=0` uses local filesystem.
- `ENABLE_GEOSERVER=1` enables GeoServer checks in scripts.
- Configure `EMAIL_*` vars to enable password reset emails in non-dev environments.

## Environment variables reference

Core:
- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `ENVIRONMENT`
- `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_TIME_ZONE`

Database:
- `DATABASE_URL` (optional; overrides other DB settings)
- `NBMS_DB_NAME`, `NBMS_DB_USER`, `NBMS_DB_PASSWORD`
- `NBMS_TEST_DB_NAME` (defaults to test database)
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `ENABLE_GIS` to toggle PostGIS usage

Storage and media:
- `USE_S3`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
- `S3_BUCKET`, `S3_REGION`, `S3_ADDRESSING_STYLE`

Reporting and exports:
- `EXPORT_REQUIRE_SECTIONS` (set to 1 to block export when required sections are missing)
- `EXPORT_REQUIRE_READINESS` (set to 1 to block export when catalog readiness is not satisfied)

Security and monitoring:
- `RATE_LIMIT_LOGIN`, `RATE_LIMIT_PASSWORD_RESET`, `RATE_LIMIT_WORKFLOW`
- `RATE_LIMIT_EXPORTS`, `RATE_LIMIT_PUBLIC_API`, `RATE_LIMIT_METRICS`
- `METRICS_TOKEN` (optional; protects /metrics when set)
- `DJANGO_LOG_JSON` (set `1` for JSON logs with request correlation)
- `CONTENT_SECURITY_POLICY`, `CONTENT_SECURITY_POLICY_REPORT_ONLY`

BIRDIE integration:
- `BIRDIE_BASE_URL` (optional live API base URL)
- `BIRDIE_API_TOKEN` (optional bearer token)
- `BIRDIE_TIMEOUT_SECONDS`
- `BIRDIE_USE_FIXTURE` (`1` default; deterministic fixture fallback)

Demo/admin bootstrap (local only):
- `SEED_DEMO_USERS` (default `0`)
- `ALLOW_INSECURE_DEMO_PASSWORDS` (default `0`; required for username=password demo logins)
- `NBMS_ADMIN_USERNAME`, `NBMS_ADMIN_EMAIL`, `NBMS_ADMIN_PASSWORD`
- Optional: `NBMS_ADMIN_FIRST_NAME`, `NBMS_ADMIN_LAST_NAME`

## Demo & Admin Verification

Local Docker demo bootstrap (dev profile only):

```
$env:SEED_DEMO_USERS='1'
$env:ALLOW_INSECURE_DEMO_PASSWORDS='1'
$env:NBMS_ADMIN_USERNAME='admin_local'
$env:NBMS_ADMIN_EMAIL='admin@example.org'
$env:NBMS_ADMIN_PASSWORD='change-me-now'
docker compose --profile minimal up -d --build
```

If the stack is already running:

```
docker compose exec backend python manage.py seed_demo_users
docker compose exec backend python manage.py ensure_system_admin
docker compose exec backend python manage.py list_demo_users
```

Login URLs:
- App: `http://localhost:8081/`
- Django admin: `http://localhost:8081/admin/`
- MFA login: `http://localhost:8081/account/login/`

Disable demo users and rotate credentials:
1. Set `SEED_DEMO_USERS=0` and `ALLOW_INSECURE_DEMO_PASSWORDS=0` in `.env`.
2. Reset demo user passwords in Django admin or deactivate demo accounts.
3. Rotate `NBMS_ADMIN_PASSWORD` and rerun `python manage.py ensure_system_admin`.

## Settings

- Dev settings: `config.settings.dev`
- Test settings: `config.settings.test`
- Prod settings: `config.settings.prod`

## Reporting

- Manager Report Pack preview: `/reporting/instances/<uuid>/report-pack/` (staff-only).
- Angular NR7 Builder: `/nr7-builder` (via frontend app route) with QA bar, section completion, and live preview.
- NR7 PDF export API: `/api/reporting/instances/<uuid>/nr7/export.pdf`.

## Exports

- ORT NR7 v2 (gated): `/exports/instances/<uuid>/ort-nr7-v2.json`
- Gating: readiness + instance approvals + consent checks (IPLC-sensitive content)

## Operations

- System health API (staff/system-admin): `/api/system/health`
- Programme ops API:
  - `/api/programmes`
  - `/api/programmes/<uuid>`
  - `/api/programmes/<uuid>/runs`
  - `/api/programmes/runs/<uuid>`
- Programme ops commands:
  - `python manage.py seed_programme_ops_v1`
  - `python manage.py run_monitoring_programmes --limit 10`
- Backup/restore helpers:
  - PowerShell: `scripts/backup_stack.ps1`, `scripts/restore_stack.ps1`
  - POSIX: `scripts/backup_stack.sh`, `scripts/restore_stack.sh`
  - Runbook: `docs/ops/BACKUP_RESTORE.md`

## Reference catalog UI

Catalog-first workflows now live in the non-admin UI:

- Create catalog datasets at `/datasets/` and link them to programmes, methodologies, and indicators.
- Manage programmes, methodologies, agreements, and sensitivity classes under `/catalog/*`.
- Use release-mode readiness checks with:
  `python manage.py reporting_readiness --instance <uuid> --format json --scope selected --mode release`

## Rulesets

ValidationRuleSet controls which sections and metadata fields are required for readiness checks.
The readiness service uses the active ruleset (by default `7NR_DEFAULT`).

Seed defaults:

```
python manage.py seed_validation_rules
```

You can override the rules in the admin UI, but keep only one active ruleset unless you
intentionally want multiple active configurations.

## Branching and releases

- `main` is the integrated release branch and source of truth.
- Feature work happens on `feat/*` branches and merges via PRs.
- Keep PRs small; ensure tests are green before merge.
- Tags (e.g., `v0.3-manager-pack`) mark release snapshots.
- `rescue/*` branches capture recovery snapshots; treat as read-only.
- Start new work from `main` and cut a fresh `feat/*` branch.

## Known limitations

- Report pack is HTML only; use print-to-PDF for now.
- Programme scheduler is command-driven; optional always-on worker profile is planned.
