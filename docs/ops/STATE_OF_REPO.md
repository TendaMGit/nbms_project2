# STATE OF REPO - NBMS Project 2

Captured: 2026-01-30 (local)

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

## E. Local development runbook (Windows, no Docker)
Assumptions:
- Postgres is running locally.
- `DATABASE_URL` points to `nbms_project2_db` (or set NBMS_* vars instead).
- GIS disabled: `ENABLE_GIS=false` (avoids GDAL/GEOS on Windows).

PowerShell (example):
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
- Local branches not merged (potentially relevant): `feat/alignment-integration-ui`, `feat/db-schema-docs`, `feat/framework-goals`, `feat/internal-review-dashboard`, `feat/ort-export-v1`, `feat/ort-template-conformance`, `feat/post-merge-hardening`, `feat/windows-infra-doctor`, `pr-1-reference-catalog-inventory`, `pr-2-reference-catalog-registry`, `pr-3-readiness-diagnostics`, `pr-4-demo-seed-walkthrough`, `pr-5-readiness-gating-snapshots`, `pr-6-readiness-governance-hardening`, `pr-7-catalog-ui-governance`, `rescue/local-state-20260115`.
- Phase 6A snapshots/diff: merged into `main` (branch `feat/reporting-snapshots-diff` is in merged list).
- Stashes (names only):
  - `stash@{0}`: WIP before switching to main (file lock fix)
  - `stash@{1}`: wip alignment integration fixes
  - `stash@{2}`: phase5-review
  - `stash@{3}`: phase4c+phase5

## H. Known risks / tech debt
- OneDrive file locks: repo lives under OneDrive; sync can lock SQLite or migration files. Recommended dev location: `C:\dev\nbms_project2` (avoid sync, reduce file lock and path-length issues).
- GIS/GDAL portability: enabling GIS on Windows requires GDAL/GEOS paths; keep `ENABLE_GIS=false` unless GIS is required.
- Docs drift: `README.md` still says "ORT mapping is a stub and not a full 7NR export," but ORT NR7 v2 is implemented in code; update docs when ready.
- Local `.env` exists but is ignored by git; keep secrets out of the repo and rotate if ever committed.
