# SECURITY_GOVERNANCE_REVIEW

## Executive Summary
NBMS already has a meaningful governance baseline (RBAC/ABAC filters, object-level permissions via guardian, consent records, audit signals, export approvals). The highest remaining risk is not missing primitives, but inconsistent enforcement across all entry points and insufficient operational hardening depth (CI security gates, metrics persistence, policy headers).

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

### Findings
- `Improved`: staff-protected route policy metadata is now centralized.
  - Policy matrix: `src/nbms_app/services/policy_registry.py`
  - Coverage guard tests: `src/nbms_app/tests/test_policy_registry.py`
  - Decorator resolves policy by URL name/function name: `src/nbms_app/views.py`
  - Remaining risk: role-gated non-staff endpoints still require explicit per-view checks.
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
- No CSP headers configured in settings.
- No explicit CORS policy module configured.
- Metrics storage is in-memory only (`src/nbms_app/services/metrics.py`), so counts are process-local.
- SAST is still missing; baseline secret/dependency checks are now in CI.

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
- CI hardening baseline:
  - Added split CI workflow with fast checks, Linux full tests, Windows smoke, and security baseline in `.github/workflows/ci.yml`.

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

