# SECURITY_GOVERNANCE_REVIEW

## Executive Summary
NBMS has a strong governance baseline (RBAC/ABAC filters, object-level permissions via guardian, consent records, audit signals, export approvals). The newest risk surface is the expanded `/api/*` layer for Angular: controls are mostly correct, but endpoint-by-endpoint policy standardization and deeper CI security checks remain ongoing work.

## 2026-02-07 Hardening Increment (Phases 4-7)

Implemented:
- GBF method runtime governance:
  - `IndicatorMethodProfile` + `IndicatorMethodRun` add explicit execution readiness and run history.
  - SDK runner writes audit events per method run (`indicator_method_run`).
- Ramsar template-pack controls:
  - endpoint-level instance scope remains enforced in `/api/template-packs/*`.
  - added pack QA endpoint and PDF export endpoint with existing instance-scope checks.
- BIRDIE integration governance:
  - BIRDIE dashboard endpoint is authenticated and scoped through programme ABAC filters.
  - lineage model (`IntegrationDataAsset`) records source/layer/hash for traceability.
- Report product governance:
  - report-product preview/export endpoints are authenticated.
  - optional instance binding is validated through `_require_instance_scope`.
- CI hardening expansion:
  - docker smoke now includes Playwright e2e smoke against nginx-served SPA.

## 2026-02-06 Hardening Increment (Phase 1)

Implemented:
- Request-ID correlation and propagation:
  - Middleware: `src/nbms_app/middleware_request_id.py`
  - Logging filter/formatter: `src/nbms_app/logging_utils.py`
  - nginx forward header: `docker/frontend/nginx.conf`
- Security header hardening:
  - CSP + cookie/session hardening in `src/config/settings/prod.py`
  - Security header middleware in `src/nbms_app/middleware_security.py`
- Session fixation mitigation:
  - one-time post-auth session key cycle in `SessionSecurityMiddleware`
  - test coverage in `src/nbms_app/tests/test_session_security.py`
- Rate limit expansion:
  - exports, public API reads, metrics/system health in `src/config/settings/base.py`
  - middleware coverage in `src/nbms_app/tests/test_rate_limiting.py`
- Operational visibility:
  - staff-only system health API `GET /api/system/health` in `src/nbms_app/api_spa.py`
  - Angular System Health UI page (`frontend/src/app/pages/system-health-page.component.ts`)
- CI security baseline expansion:
  - Bandit SAST + Trivy filesystem/image scans in `.github/workflows/ci.yml`
- Critical workflow audit coverage tests:
  - `src/nbms_app/tests/test_audit_transition_coverage.py`
- NR7 builder API hardening:
  - instance-scoped, authenticated reporting APIs (`/api/reporting/instances*`) in `src/nbms_app/api_spa.py`
  - QA checks composed from readiness + explicit required-field validation (`src/nbms_app/services/nr7_builder.py`)

## 2026-02-06 Programme Ops Governance Increment (Phase 3)

Implemented:
- Programme ops ABAC/no-leak endpoints:
  - `/api/programmes`, `/api/programmes/{uuid}`, `/api/programmes/{uuid}/runs`, `/api/programmes/runs/{uuid}`
  - object lookups resolve through filtered programme querysets (`src/nbms_app/api_spa.py`).
- Steward-aware authorization:
  - `filter_monitoring_programmes_for_user` and `can_edit_monitoring_programme` now include active steward assignments (`src/nbms_app/services/catalog_access.py`).
- Operational auditability:
  - run queue/start/complete/fail events are written through `record_audit_event` in `src/nbms_app/services/programme_ops.py`.
- Lineage and QA traceability:
  - `MonitoringProgrammeRun`, `MonitoringProgrammeRunStep`, and `MonitoringProgrammeAlert` store run-level provenance and alerts.
- Regression tests:
  - `src/nbms_app/tests/test_api_programme_ops.py`
  - `src/nbms_app/tests/test_programme_ops_commands.py`

## RBAC + Object-Level Access Findings

### What is implemented
- Canonical roles and checks:
  - `src/nbms_app/services/authorization.py`
  - `src/nbms_app/roles.py`
- System admin model:
  - `is_system_admin` supports superuser, `SystemAdmin` group, or `nbms_app.system_admin` permission.
- ABAC queryset filtering:
  - `filter_queryset_for_user` enforces status/sensitivity/org/creator constraints.
- Object-level support:
  - guardian `get_objects_for_user` is applied when `perm` is passed to `filter_queryset_for_user`.
- Catalog access policy:
  - dataset/programme/methodology/agreement/sensitivity filters in `src/nbms_app/services/catalog_access.py`.
- Spatial ABAC policy:
  - layer/feature filters in `src/nbms_app/services/spatial_access.py`
  - tests in `src/nbms_app/tests/test_api_spatial.py`

### Findings
- `Improved`: staff-protected route policy metadata is now centralized.
  - Policy matrix: `src/nbms_app/services/policy_registry.py`
  - Coverage guard tests: `src/nbms_app/tests/test_policy_registry.py`
  - Decorator resolves policy by URL name/function name: `src/nbms_app/views.py`
  - Remaining risk: role-gated non-staff endpoints still require explicit per-view checks.
- `Improved`: new Angular-facing APIs use ABAC-filtered querysets and object lookup patterns.
  - `/api/indicators*`, `/api/spatial*`, `/api/template-packs*` in `src/nbms_app/api_spa.py`
  - direct ABAC leakage checks added for spatial APIs (`test_api_spatial.py`).
- `Partial`: guardian checks are not universal.
  - Where `perm` is omitted in `filter_queryset_for_user`, authorization is ABAC-only.
  - This is intentional in places but should be explicit per endpoint category.

## Consent + Sensitivity Gating Findings

### What is implemented
- Consent model and status transitions:
  - `ConsentRecord`, `ConsentStatus` in `src/nbms_app/models.py`
  - `set_consent_status` in `src/nbms_app/services/consent.py`
- Gating points:
  - Approval block on missing consent in `approve_for_instance` (`instance_approvals.py`)
  - Release block in `release_export` (`exports.py`)
  - Consent-aware data filters in `indicator_data.py`

### Findings
- `Strong baseline`, `partial breadth`:
  - Export-focused flows are strongly gated.
  - Catalog and read surfaces do not all express consent state consistently as first-class policy metadata.
- `Important fix delivered in this review`:
  - Single-item export approval now blocks non-published objects in `reporting_instance_approval_action` (`src/nbms_app/views.py`).

## Audit Coverage Findings

### What is implemented
- CRUD audit for almost all app models:
  - `src/nbms_app/signals_audit.py`
- Domain events:
  - workflow/approval/export/snapshot actions record explicit events (`services/workflows.py`, `services/instance_approvals.py`, `services/exports.py`, views snapshot/export actions).
- Sensitive access audits:
  - `audit_sensitive_access` in `src/nbms_app/services/audit.py`
  - API list/detail audit hook in `src/nbms_app/api.py`
- Request metadata:
  - request path/method/ip/session/request_id persisted in `AuditEvent`.
- Metadata sanitization:
  - sensitive metadata key redaction in `services/audit.py`.

### Findings
- `Implemented`, but operational controls are missing:
  - No explicit retention/purge job.
  - No immutable/WORM sink for high-assurance audit compliance.

## Security Baseline Findings

### Positive controls
- Production settings hardening:
  - secure cookies, SSL redirect, HSTS, referrer policy, frame options in `src/config/settings/prod.py`
- Rate limit middleware:
  - `src/nbms_app/middleware.py`
- CSRF middleware and Django auth defaults enabled in `src/config/settings/base.py`.

### Gaps
- No explicit CORS policy module configured.
- Metrics storage is in-memory only (`src/nbms_app/services/metrics.py`), so counts are process-local.
- SAST baseline exists (Bandit), but Semgrep-style rule coverage is still missing.
- Frontend dependency and bundle integrity policies are not yet pinned by lockfile verification in backend CI jobs.

## Immediate Fixes Applied in This Tightening Pass
- Metrics token handling tightened:
  - Constant-time token comparison via `secrets.compare_digest`.
  - Query token disabled by default unless `METRICS_ALLOW_QUERY_TOKEN=true`.
  - Files: `src/nbms_app/views_metrics.py`, `src/config/settings/base.py`, `.env.example`, tests in `src/nbms_app/tests/test_metrics.py`.
- Production secure defaults tightened and tested:
  - `src/config/settings/prod.py`, tests in `src/nbms_app/tests/test_prod_settings.py`.
- Export approval correctness tightened:
  - Prevent non-published objects from single-item approval in `src/nbms_app/views.py`.
  - tests: `src/nbms_app/tests/test_reporting_approvals_ui.py`, `src/nbms_app/tests/test_reporting_freeze.py`.
- Route-policy normalization baseline:
  - Added endpoint policy matrix in `src/nbms_app/services/policy_registry.py`.
  - Added coverage tests in `src/nbms_app/tests/test_policy_registry.py`.
- New API governance surface:
  - Added session+CSRF bootstrap APIs: `/api/auth/me`, `/api/auth/csrf`.
  - Added template-pack runtime APIs and spatial GeoJSON APIs with ABAC filtering.
  - Added dedicated API tests: `test_api_spa_auth.py`, `test_api_indicator_explorer.py`, `test_api_spatial.py`, `test_api_template_packs.py`.
- CI hardening baseline:
  - Added split CI workflow with fast checks, Linux full tests, Windows smoke, security baseline, frontend build/tests, and Docker minimal profile smoke in `.github/workflows/ci.yml`.

## Medium-Term Governance Plan
1. Make endpoint policy classification explicit.
- Add a route-policy map (view -> required role + object scope + consent behavior) and enforce with shared decorators.
2. Add audit retention + export controls.
- Scheduled retention policy and signed audit export bundles.
3. Add CI security gates.
- Add secret scanning + dependency vulnerability scanning + `manage.py check --deploy` on prod-profile settings.
4. Harden policy headers.
- Add CSP and explicit `SECURE_*` coverage tests.
5. Unify object-level authorization assertions in tests.
- Parameterized access matrix tests for critical endpoints (`views.py`, `api.py`, export/snapshot/review paths).

