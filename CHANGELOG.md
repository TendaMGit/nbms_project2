# Changelog

## Unreleased

Highlights:
- Phase 3 monitoring programme operations uplift:
  - Extended `MonitoringProgramme` with operational controls (`refresh_cadence`, scheduler fields, pipeline/rules JSON, lineage notes, operating institutions).
  - Added programme steward assignments and ABAC-aware steward visibility/edit support.
  - Added programme run runtime models:
    - `MonitoringProgrammeRun`
    - `MonitoringProgrammeRunStep`
    - `MonitoringProgrammeAlert`
  - Added programme operations API endpoints:
    - `GET /api/programmes`
    - `GET /api/programmes/{uuid}`
    - `POST /api/programmes/{uuid}/runs`
    - `GET|POST /api/programmes/runs/{uuid}`
  - Added programme operations Angular workspace in `frontend/src/app/pages/programme-ops-page.component.ts`.
  - Added management commands:
    - `seed_programme_ops_v1`
    - `run_monitoring_programmes`
  - Added programme ops tests (`test_api_programme_ops.py`, `test_programme_ops_commands.py`) and frontend component test.
- Phase 2 NR7 authoring uplift:
  - Added Angular NR7 Report Builder workspace in `frontend/src/app/pages/reporting-page.component.ts` with:
    - section completion nav,
    - QA bar (blockers/warnings),
    - preview panel,
    - direct links to structured section editors,
    - PDF export action.
  - Added backend NR7 builder APIs:
    - `/api/reporting/instances`
    - `/api/reporting/instances/{uuid}/nr7/summary`
    - `/api/reporting/instances/{uuid}/nr7/export.pdf`
  - Added NR7 validation engine and preview composition service (`src/nbms_app/services/nr7_builder.py`).
  - Added server-side PDF rendering template and pipeline.
- Phase 1 hardening increment:
  - Added request-ID propagation end-to-end (`X-Request-ID`) with middleware and log correlation.
  - Added structured JSON logging option (`DJANGO_LOG_JSON=1`) and request-id log filter.
  - Added production CSP baseline and security header middleware.
  - Added authenticated/staff-only system health API (`/api/system/health`) and Angular System Health page.
  - Expanded rate limits for exports, public API reads, and metrics endpoints.
  - Expanded CI security baseline with Bandit SAST and Trivy filesystem/image scans.
  - Added backup/restore helper scripts for PostGIS + MinIO with runbook (`docs/ops/BACKUP_RESTORE.md`).
  - Added audit coverage tests for critical transitions (export submit/approve/release; indicator/dataset publish).
- Added Angular primary app (`frontend/`) with dashboard, indicator explorer/detail, spatial map viewer, reporting launcher, and template-pack pages.
- Added SPA/BFF API layer under `/api/*`:
  - auth/help: `/api/auth/me`, `/api/auth/csrf`, `/api/help/sections`
  - dashboard: `/api/dashboard/summary`
  - indicators: `/api/indicators*` detail/datasets/series/validation/transition
  - spatial: `/api/spatial/layers`, `/api/spatial/layers/{slug}/features`
  - template packs: `/api/template-packs*`
- Added spatial runtime models and services:
  - `SpatialLayer`, `SpatialFeature` and ABAC filter service in `src/nbms_app/services/spatial_access.py`
  - demo spatial seed command: `seed_spatial_demo_layers`
- Added multi-MEA template-pack runtime scaffolding:
  - `ReportTemplatePack`, `ReportTemplatePackSection`, `ReportTemplatePackResponse`
  - pack seed command: `seed_mea_template_packs`
  - exporter registry: `src/nbms_app/services/template_pack_registry.py`
- Added GBF/NBA-inspired indicator workflow seed pack:
  - command: `seed_indicator_workflow_v1`
  - includes 4 end-to-end indicators with methodology/dataset/series/evidence/programme links
- Added Docker-first full-stack runtime at repo root:
  - `compose.yml` with `minimal`, `full`, `spatial` profiles
  - backend and frontend Dockerfiles plus nginx reverse proxy config
- Expanded CI:
  - new `frontend-build` job
  - new `docker-minimal-smoke` job
- ORT NR7 v2 exporter now maps structured Section I/II/V models and enriched Section III/IV data, including Section IV goal progress and binary indicator group comments.
- Added export payload contract validation service (`src/nbms_app/services/export_contracts.py`) with tests and golden fixture refresh flow.
- Added centralized section field help dictionary and rendered field-level help/tooltips for Section I-V templates.
- Added route policy registry (`src/nbms_app/services/policy_registry.py`) and policy coverage tests (`src/nbms_app/tests/test_policy_registry.py`).
- Added split CI baseline workflow (`.github/workflows/ci.yml`) with Linux full tests, Windows smoke, and security checks.
- Hardened staff-only decorator behavior for non-regression (redirect contract preserved) and snapshot strict-user handling.
- Docker compose minio init image pin corrected to restore baseline startup.

## v0.3-manager-pack

Highlights:
- ValidationRuleSet seeding and reporting defaults helper commands
- Manager Report Pack preview with readiness score and appendices
- Readiness panels and instance readiness scoring
- Reporting cycles, instances, approvals, and consent gating
- Export packages with instance-scoped approvals

Breaking changes:
- None noted; run migrations and seed reporting defaults after upgrade.

Upgrade notes:
1) python manage.py migrate
2) python manage.py bootstrap_roles
3) python manage.py seed_reporting_defaults
