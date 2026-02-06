# STATE OF REPO - NBMS Project 2

## One Biodiversity Hardening V1 - Phase 0 Baseline (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Base branch/commit: `feat/ui-spatial-indicators-v1` @ `cc22263`

Commands executed (host):
- `python --version` -> `Python 3.13.4`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `324 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py check` -> no issues
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations --check --dry-run` -> no changes detected

Commands executed (docker):
- `docker compose --profile minimal up -d --build` -> backend/frontend/core services started
- `docker compose --profile minimal ps` -> backend/frontend/postgis/redis/minio healthy
- `Invoke-WebRequest http://127.0.0.1:8000/health/` -> `{"status": "ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/` -> `200`
- `Invoke-WebRequest http://127.0.0.1:8081/health/` -> `{"status": "ok"}`

Baseline status:
- Host baseline: PASS
- Docker baseline: PASS
- Proceeding to Phase 1 hardening

## One Biodiversity Hardening V1 - Phase 1 Hardening (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Commit base for phase: `cc22263`

Commands executed:
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q src/nbms_app/tests/test_request_id.py src/nbms_app/tests/test_rate_limiting.py src/nbms_app/tests/test_api_system_health.py src/nbms_app/tests/test_session_security.py src/nbms_app/tests/test_prod_settings.py src/nbms_app/tests/test_api_spa_auth.py src/nbms_app/tests/test_audit_transition_coverage.py` -> `16 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `334 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py check` -> no issues
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations --check --dry-run` -> no changes detected
- `npm --prefix frontend run test` -> `2 passed`
- `npm --prefix frontend run build` -> pass
- `docker compose --profile minimal up -d --build` -> pass
- `Invoke-WebRequest http://127.0.0.1:8000/health/` -> `{"status":"ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/health/` -> `{"status":"ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/api/help/sections` -> `200`

Implemented in phase:
- Request-ID middleware and log correlation.
- CSP/security header middleware and production defaults.
- Session fixation mitigation (single rekey after auth).
- Expanded rate limits (exports/public API/metrics).
- System health API + Angular page.
- CI security additions: Bandit + Trivy.
- Backup/restore helper scripts and runbook.

## One Biodiversity Hardening V1 - Phase 2 NR7 Builder Uplift (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Base commit for phase: `7f533d8`

Commands executed:
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q src/nbms_app/tests/test_api_nr7_builder.py src/nbms_app/tests/test_api_spa_auth.py src/nbms_app/tests/test_request_id.py` -> `9 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `337 passed`
- `npm --prefix frontend run test` -> `4 passed`
- `npm --prefix frontend run build` -> pass
- `docker compose --profile minimal up -d --build` -> pass
- `Invoke-WebRequest http://127.0.0.1:8000/health/` -> `{"status":"ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/health/` -> `{"status":"ok"}`

Implemented in phase:
- Added NR7 builder APIs for instance listing, QA/preview summary, and PDF export.
- Added validation engine for required fields, cross-section checks, and readiness integration.
- Added Angular NR7 Report Builder page with QA bar, section completion list, live preview, and PDF action.
- Added richer section-help payload (`sections_rich`) for contextual guidance.
- Added PDF runtime dependencies to backend Docker image and requirements.

## UI/Spatial/Indicator Increment Verification (2026-02-06)
- Branch: `feat/ui-spatial-indicators-v1`
- Base commit at start of increment: `db98d16`

Commands executed (host):
- `python --version`
- `python -m pip install -r requirements.txt`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py check`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations --check --dry-run`
- `cd frontend; npm run build`
- `cd frontend; npm run test`
- `docker compose --profile minimal up -d --build`
- `docker compose --profile full up -d`
- `docker compose --profile minimal ps`
- `Invoke-WebRequest http://127.0.0.1:8000/health/`
- `Invoke-WebRequest http://127.0.0.1:8081/health/`
- `Invoke-WebRequest http://127.0.0.1:8081/api/help/sections`
- `Invoke-WebRequest http://127.0.0.1:8081/api/indicators?status=published`
- `Invoke-WebRequest http://127.0.0.1:8081/api/spatial/layers`

Result summary:
- Backend test suite: `324 passed`
- Django checks: clean (`No changes detected` for migrations)
- Frontend: Angular build passes; frontend tests pass (`2 passed`)
- Docker minimal profile: backend + frontend + PostGIS + Redis + MinIO healthy
- Docker full profile: starts GeoServer on `http://127.0.0.1:8080/`
- Health checks:
  - backend direct `/health/` -> `{"status": "ok"}`
  - frontend-proxied `/health/` -> `{"status": "ok"}`
- API checks:
  - `/api/help/sections` status `200`
  - `/api/indicators?status=published` returns seeded GBF workflow indicators
  - `/api/spatial/layers` returns seeded map layer metadata

## BASELINE VERIFIED (2026-02-06)
- Branch: `feat/nr7-full-conformance-integration`
- Commands executed (Windows host):
  - `git status`
  - `git branch`
  - `python --version`
  - `python -m pip install -r requirements.txt`
  - `python -m pip install -r requirements-dev.txt`
  - `$env:DJANGO_SETTINGS_MODULE='config.settings.test'; $env:PYTHONPATH="$PWD\src"; pytest -q`
  - `python manage.py check`
  - `python manage.py migrate`
  - `python manage.py runserver`
  - health checks: `GET /health/`, `GET /health/storage/`
- Result summary:
  - local suite: `308 passed`
  - `check` and `migrate` succeeded
  - `/health/` returned `{"status":"ok"}`
  - `/health/storage/` returned `{"status":"disabled","detail":"USE_S3=0"}`
- Docker baseline:
  - `docker compose -f docker/docker-compose.yml up -d` verified after fixing `minio-init` image tag to `minio/mc:latest`.

## Snapshot scope
- Audited commit (main): `d4efd3f8d7cf6b9a7fea98586c40ee54f44e9559`
- Captured at: 2026-01-30 10:17 (local) before docs branch `feat/docs-repo-state`
- Verified: `git log -1 main` matched the audited commit at capture time
- Included: code and docs on `main` at the audited commit
- Excluded: docs-only edits on this branch, unmerged feature branches, and local stashes
- Authoritative docs note: This file is the authoritative Windows-first runbook unless superseded

## A. Repo metadata
- Repo root: `C:\Users\T.Munyai\OneDrive\Apps\NMSI\About GBF development_Draft for prep\nbms_project2`
- Git status (captured before docs branch): `## main...origin/main`
- HEAD commit (captured before docs branch): `d4efd3f8d7cf6b9a7fea98586c40ee54f44e9559`
- Branch (captured before docs branch): `main`
- Python: `3.13.4`
- Django: `5.2.9`
- Pip top-level (from `python -m pip list --not-required`):
  - `boto3==1.34.162`
  - `celery==5.4.0`
  - `dj-database-url==2.2.0`
  - `django-filter==24.3`
  - `django-geojson==4.2.0`
  - `django-guardian==2.4.0`
  - `django-leaflet==0.33.0`
  - `django-storages==1.14.3`
  - `django-two-factor-auth==1.17.0`
  - `drf-spectacular==0.28.0`
  - `drf-spectacular-sidecar==2024.7.1`
  - `openpyxl==3.1.5`
  - `pdfplumber==0.11.9`
  - `phonenumbers==8.13.40`
  - `pip-tools==7.5.2`
  - `playwright==1.52.0`
  - `psycopg2-binary==2.9.10`
  - `Pygments==2.19.2`
  - `pytest-django==4.10.0`
  - `python-docx==1.2.0`
  - `python-dotenv==1.0.1`
  - `redis==5.0.8`
  - `xhtml2pdf==0.2.17`

## B. Features inventory

| Feature | Status (main/branch) | Primary files | Routes/Commands | Gating summary | Tests |
| --- | --- | --- | --- | --- | --- |
| ORT NR7 export v2 (`nbms.ort.nr7.v2`) + strict gating + deterministic output | main (merged from `feat/ort-nr7-export-v2`) | `src/nbms_app/exports/ort_nr7_v2.py`<br>`src/nbms_app/services/exports.py`<br>`src/nbms_app/services/section_progress.py`<br>`src/nbms_app/services/indicator_data.py`<br>`src/nbms_app/views.py`<br>`src/nbms_app/urls.py`<br>`docs/exports/ort_nr7_v2_export.md` | `/exports/instances/<uuid>/ort-nr7-v2.json` (option `?download=1`) | `assert_instance_exportable` enforces readiness + approvals; `_require_referential_integrity` blocks unapproved/ABAC/consent-violating references; scoped targets via `scoped_national_targets`/`scoped_framework_targets`; deterministic ordering via stable JSON + sorted lists | `src/nbms_app/tests/test_ort_nr7_v2_export.py` |
| Internal review dashboard + Review Pack v2 | main (branch `feat/internal-review-dashboard` has unmerged commits) | `src/nbms_app/views.py`<br>`src/nbms_app/services/review.py`<br>`src/nbms_app/services/review_decisions.py`<br>`templates/nbms_app/reporting/review_dashboard.html`<br>`templates/nbms_app/reporting/review_pack_v2.html` | `/reporting/instances/<uuid>/review/`<br>`/reporting/instances/<uuid>/review-pack-v2/`<br>`/reporting/instances/<uuid>/review-decisions/` | Staff-only + instance ABAC via `_require_section_progress_access`; strict user proxy removes staff bypass; consent filters applied to evidence/releases; scoped targets and approved items only | `src/nbms_app/tests/test_review_dashboard.py`<br>`src/nbms_app/tests/test_review_decisions.py` |
| Structured Section III/IV progress models + instance-scoped ABAC + frozen POST blocking | main (merged from `feat/section-iii-iv-structured-storage`) | `src/nbms_app/models.py` (SectionIII/IV)<br>`src/nbms_app/services/section_progress.py`<br>`src/nbms_app/forms.py`<br>`src/nbms_app/views.py`<br>`templates/nbms_app/reporting/section_iii_*`<br>`templates/nbms_app/reporting/section_iv_*` | `/reporting/instances/<uuid>/section-iii/`<br>`/reporting/instances/<uuid>/section-iv/` | `_require_section_progress_access` enforces instance-scoped approvals + ABAC; `scoped_national_targets`/`scoped_framework_targets` filter visibility; frozen instances set read-only and block POST unless admin override | `src/nbms_app/tests/test_section_progress.py`<br>`src/nbms_app/tests/test_reporting_freeze.py` |
| Alignment framework registries + mapping tables (Framework/Goal/Target/Indicator + link models) | main (merged from multiple `feat/*` branches) | `src/nbms_app/models.py` (Framework*, link models)<br>`src/nbms_app/services/alignment.py`<br>`src/nbms_app/views.py`<br>`src/nbms_app/forms_catalog.py`<br>`src/nbms_app/migrations/0017_*`<br>`src/nbms_app/migrations/0022_*`<br>`src/nbms_app/migrations/0026_*` | `/frameworks/`, `/framework-targets/`, `/framework-indicators/`<br>`/catalog/frameworks/`, `/catalog/framework-goals/`, `/catalog/framework-targets/`, `/catalog/framework-indicators/`<br>`python manage.py import_alignment_mappings` / `export_alignment_mappings` | ABAC via `filter_queryset_for_user`; catalog manager required for CRUD; link filters enforce `is_active` and ABAC on both sides; cross-framework integrity validated | `src/nbms_app/tests/test_alignment_mappings.py`<br>`src/nbms_app/tests/test_cross_framework_integrity.py` |
| Indicator data series/points + binary indicator questions/responses + ABAC+consent filters | main (merged from `feat/indicator-and-binary-data-models`) | `src/nbms_app/models.py` (IndicatorDataSeries/Point, BinaryIndicatorQuestion/Response)<br>`src/nbms_app/services/indicator_data.py`<br>`src/nbms_app/management/commands/seed_binary_indicator_questions.py`<br>`src/nbms_app/management/commands/import_indicator_data.py`<br>`src/nbms_app/management/commands/export_indicator_data.py` | `python manage.py seed_binary_indicator_questions`<br>`python manage.py import_indicator_data`<br>`python manage.py export_indicator_data` | ABAC via `filter_queryset_for_user`; consent filter applied to IPLC-sensitive series/questions; points limited by allowed series and dataset releases | `src/nbms_app/tests/test_indicator_data.py` |
| Reporting snapshots + diff (Phase 6A) | main (merged from `feat/reporting-snapshots-diff`) | `src/nbms_app/models.py` (ReportingSnapshot)<br>`src/nbms_app/services/snapshots.py`<br>`src/nbms_app/views.py`<br>`templates/nbms_app/reporting/snapshots_list.html`<br>`templates/nbms_app/reporting/snapshot_detail.html`<br>`templates/nbms_app/reporting/snapshot_diff.html` | `/reporting/instances/<uuid>/snapshots/`<br>`/reporting/instances/<uuid>/snapshots/create/`<br>`/reporting/instances/<uuid>/snapshots/diff/` | Snapshot creation uses ORT NR7 v2 export gating (readiness + approvals) with strict user proxy; views require staff + instance ABAC; snapshots are immutable and deduped by payload hash | `src/nbms_app/tests/test_reporting_snapshots.py` |

## C. Domain model summary (entities + key relationships)
- Core identity + ABAC (0001, 0004): `User`, `Organisation`, plus lifecycle/sensitivity fields and ABAC scaffolding in `src/nbms_app/models.py`.
- Reporting core (0011-0016): `ReportingCycle` -> `ReportingInstance`; `InstanceExportApproval` (content_type + object_uuid + scope); `ExportPackage`; `ConsentRecord`; `ReportSectionTemplate`/`ReportSectionResponse`; `ValidationRuleSet`.
- Catalog + evidence/data (0009-0010, 0025-0026): `Dataset`, `DatasetRelease`, `Evidence`, `License`, `SourceDocument` plus QA/metadata fields.
- Alignment registry (0017, 0022, 0026): `Framework` -> `FrameworkGoal` -> `FrameworkTarget` -> `FrameworkIndicator`; mapping tables `NationalTargetFrameworkTargetLink` and `IndicatorFrameworkIndicatorLink`.
- Indicator data + binary questions (0018): `IndicatorDataSeries` (exclusive FK to `Indicator` or `FrameworkIndicator`) -> `IndicatorDataPoint` (optional `DatasetRelease`); `BinaryIndicatorQuestion` -> `BinaryIndicatorResponse` (per `ReportingInstance`).
- Structured progress (0019): `SectionIIINationalTargetProgress` (ReportingInstance + NationalTarget) and `SectionIVFrameworkTargetProgress` (ReportingInstance + FrameworkTarget), each with M2M links to series, binary responses, evidence, and dataset releases.
- Snapshots + review decisions (0020-0023): `ReportingSnapshot` (immutable, hash-deduped) and `ReviewDecision` (immutable, tied to snapshot).
- Reference catalog expansions (0022-0024): `SensitivityClass`, `DataAgreement`, `DatasetCatalog`, `MonitoringProgramme`, `Methodology` + `MethodologyVersion`, and link tables for dataset/indicator/methodology/programme relationships.

## D. Workflows summary
- ReportingInstance lifecycle: `ReportingStatus` supports `draft -> pending_review -> approved -> released -> archived` in `src/nbms_app/models.py`. In practice, gating is enforced via approvals, readiness checks, snapshots, and review decisions rather than explicit status transitions.
- Freeze/override: `reporting_instance_freeze` sets `frozen_at`/`frozen_by` (`src/nbms_app/views.py`); non-admin edits and approvals are blocked while frozen; admin override allowed for approvals and unfreeze.
- Instance-scoped approvals: `InstanceExportApproval` is keyed by content type + object UUID + scope; `approved_queryset` powers readiness, review summaries, and exports (`src/nbms_app/services/instance_approvals.py`).
- Consent/IPLC gating: `requires_consent` + `ConsentRecord` (instance-specific or global) enforce IPLC-sensitive visibility; approvals and exports block without consent; indicator data filters apply consent gating (`src/nbms_app/services/consent.py`, `src/nbms_app/services/indicator_data.py`).
- Export gating: `assert_instance_exportable` enforces readiness + approvals; ORT NR7 v2 export also enforces referential integrity across referenced series/evidence/releases; `EXPORT_REQUIRE_SECTIONS` and `EXPORT_REQUIRE_READINESS` can hard-block exports (`src/nbms_app/services/exports.py`, `src/nbms_app/exports/ort_nr7_v2.py`).

## E. Local development runbook (Windows, no Docker, ENABLE_GIS=false)
Assumptions:
- Postgres is running locally.
- `DATABASE_URL` points to `nbms_project2_db` (or set NBMS_* vars instead).
- GIS disabled: `ENABLE_GIS=false` (avoids GDAL/GEOS on Windows).

### 1) Postgres provisioning (psql)
Run once as a Postgres superuser:
```
# Update these values for your environment
$env:PGHOST='localhost'
$env:PGPORT='5432'
$env:PGUSER='postgres'

psql -d postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='nbms_user') THEN CREATE ROLE nbms_user LOGIN PASSWORD 'YOUR_PASSWORD'; END IF; END $$;"
psql -d postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname='nbms_project2_db') THEN CREATE DATABASE nbms_project2_db OWNER nbms_user; END IF; END $$;"
```

### 2) App setup and run (PowerShell)
```
# from repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Copy-Item .env.example .env

# Local session env (or place in .env)
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:DJANGO_DEBUG='true'
$env:ENABLE_GIS='false'
$env:DATABASE_URL='postgresql://nbms_user:YOUR_PASSWORD@localhost:5432/nbms_project2_db'
$env:USE_S3='0'

python manage.py migrate
python manage.py bootstrap_roles
python manage.py seed_reporting_defaults
python manage.py runserver
```

### 3) Known-good smoke verification
Start the server (if not already running):
```
python manage.py runserver
```

In a second PowerShell:
```
Invoke-WebRequest http://127.0.0.1:8000/health/ | Select-Object -Expand Content
Invoke-WebRequest http://127.0.0.1:8000/health/storage/ | Select-Object -Expand Content
```
Expected responses:
- `/health/` -> `{ "status": "ok" }` (DB reachable)
- `/health/storage/` with `USE_S3=0` -> `{ "status": "disabled", "detail": "USE_S3=0" }`

### Troubleshooting
- OneDrive file locks: symptoms include sporadic migration failures or file-in-use errors. Move the repo to `C:\dev\nbms_project2` to avoid sync locks.
- psycopg2 connection errors: verify `DATABASE_URL` or `NBMS_DB_NAME`, `NBMS_DB_USER`, `NBMS_DB_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`. Ensure `ENABLE_GIS=false` and no GIS-only engine is forced.
- Migrations/roles missing: run `python manage.py migrate` and `python manage.py bootstrap_roles` before first login.

GIS dependency note:
- `ENABLE_GIS` controls whether `django.contrib.gis` is installed and whether a GIS engine is used (`src/config/settings/base.py`).
- When `ENABLE_GIS=false`, the engine is forced to `django.db.backends.postgresql`, which avoids GDAL/GEOS setup on Windows.

## F. Tests and health
- Pytest (Windows):
```
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
$env:PYTHONPATH="$PWD\src"
pytest -q
```
- Targeted tests (examples):
```
pytest -q src/nbms_app/tests/test_ort_nr7_v2_export.py
pytest -q src/nbms_app/tests/test_review_dashboard.py
pytest -q src/nbms_app/tests/test_section_progress.py
```
- Health endpoints:
  - `/health/` returns `{ "status": "ok" }` if DB is reachable; otherwise 503.
  - `/health/storage/` returns `{ "status": "disabled", "detail": "USE_S3=0" }` when local storage is used; otherwise checks S3.
- Consistent warnings: no repo-documented warnings found; `scripts/test.sh` runs with `PYTHONWARNINGS=default` to surface deprecations if they appear.

## G. Branch/PR status & pending work
- Local branches (merged into main): `feat/alignment-mapping-tables`, `feat/catalog-admin-parity`, `feat/catalog-vocab-provenance`, `feat/framework-registry-crud`, `feat/gbf-preload-alignment`, `feat/indicator-and-binary-data-models`, `feat/ort-export-v1-narrative`, `feat/ort-nr7-export-v2`, `feat/phase6-domain-exports`, `feat/reporting-snapshots-diff`, `feat/review-signoff-decisions`, `feat/section-iii-iv-structured-storage`, `feat/security-governance-integrity-pack`.
- Local branches not merged (as of 2026-01-30): `feat/alignment-integration-ui`, `feat/db-schema-docs`, `feat/docs-repo-state`, `feat/docs-repo-state-polish`, `feat/framework-goals`, `feat/internal-review-dashboard`, `feat/ort-export-v1`, `feat/ort-template-conformance`, `feat/post-merge-hardening`, `feat/windows-infra-doctor`, `rescue/local-state-20260115`.
- Phase 6A snapshots/diff: merged into `main` (branch `feat/reporting-snapshots-diff` is in merged list).
- Stashes (names only):
  - `stash@{0}`: WIP before switching to main (file lock fix)
  - `stash@{1}`: wip alignment integration fixes
  - `stash@{2}`: phase5-review
  - `stash@{3}`: phase4c+phase5

### Unmerged branches triage
Merge status is from a dry-run `git merge --no-commit --no-ff main` into each branch on 2026-01-30 (no commits).

| Branch name | Last commit date | Touches migrations? | Touches auth/ABAC/consent/export gating? | Touches templates/UI only? | Merge status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `feat/alignment-integration-ui` | 2026-01-27 | Y | Y | N | Conflicts | Large cross-cutting alignment UI + governance changes; conflicts in models/views/templates. |
| `feat/db-schema-docs` | 2026-01-28 | Y | Y | N | Clean | Docs-heavy branch with governance changes; verify before merge. |
| `feat/docs-repo-state` | 2026-01-30 | N | N | N | Clean | Docs-only repo state capture (superseded by polish branch). |
| `feat/docs-repo-state-polish` | 2026-01-30 | N | N | N | Clean | Docs-only polish (current work). |
| `feat/framework-goals` | 2026-01-27 | Y | Y | N | Conflicts | FrameworkGoal lifecycle/index migration plus governance touches. |
| `feat/internal-review-dashboard` | 2026-01-29 | N | N | N | Clean | No diff vs main; candidate for cleanup. |
| `feat/ort-export-v1` | 2026-01-16 | Y | Y | N | Conflicts | Legacy ORT export + catalog work; heavy overlap with main. |
| `feat/ort-template-conformance` | 2026-01-20 | Y | Y | N | Conflicts | ORT conformance/docs + code changes; conflicts in core files. |
| `feat/post-merge-hardening` | 2026-01-29 | Y | Y | N | Clean | Audit hardening + migration 0027; review scope before merge. |
| `feat/windows-infra-doctor` | 2026-01-29 | Y | Y | N | Clean | Windows infra doctor scripts + migration 0027; review scope. |
| `rescue/local-state-20260115` | 2026-01-15 | Y | Y | N | Conflicts | Rescue snapshot; not intended for merge. |

Notes:
- "Touches auth/ABAC/consent/export gating" is flagged when a branch changes `src/nbms_app/exports/*`, `services/authorization.py`, `services/consent.py`, `services/exports.py`, `services/instance_approvals.py`, or `models.py`.
- "Touches templates/UI only" is true only when all changes are under `templates/` or `static/`.

## H. Known risks / tech debt
- OneDrive file locks: repo lives under OneDrive; sync can lock SQLite or migration files. Recommended dev location: `C:\dev\nbms_project2` (avoid sync, reduce file lock and path-length issues).
- GIS/GDAL portability: enabling GIS on Windows requires GDAL/GEOS paths; keep `ENABLE_GIS=false` unless GIS is required.
- Keep README and `docs/ops/STATE_OF_REPO.md` in sync; treat this file as the authoritative runbook.
- Local `.env` exists but is ignored by git; keep secrets out of the repo and rotate if ever committed.
