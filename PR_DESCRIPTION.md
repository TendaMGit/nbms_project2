# Security/Governance Integrity Pack PR

## What changed

### Authorization
- Defined SystemAdmin as the only unrestricted role (superuser OR SystemAdmin group OR `nbms_app.system_admin` permission).
- Removed staff-based ABAC bypasses across authorization and catalog access.
- Enforced anonymous/public list constraints (published + public + non-sensitive only).

### Audit
- Expanded `AuditEvent` schema to include request metadata and content type references.
- Added request context middleware and admin hooks for consistent audit context.
- Added audit events for sensitive reads (detail + list + API) and downloads/exports.
- Added audit redaction denylist for sensitive fields (geometry, narrative text, contact data, payloads).
- Prevented duplicate audit entries by suppressing signal-based CRUD logging during workflow/approval/export actions.

### Lifecycle / Workflow
- Routed archive actions through lifecycle/workflow services (no direct status writes in views).
- Added service-layer audit logging for workflow transitions.

### Integrity
- Enforced cross-framework integrity for goal/target/indicator relations in model `clean()` and `save()`.
- Standardized FrameworkGoal lifecycle to match catalog patterns.

### Methodology Versioning
- Added MethodologyVersion-first linkage and backfill logic.
- Updated readiness diagnostics to require active MethodologyVersion links.

### Alignments
- Added alignment management UI for national to framework targets/indicators and indicator to methodology version links.

### Exports
- Unified export approvals on `InstanceExportApproval` only.
- Added audit events for export approvals, submissions, releases, and downloads.

### API
- Added read-only API endpoints for registry entities with ABAC filtering and audited reads.

## Why (mapped to original findings)
- Staff ABAC bypass -> replaced with `is_system_admin()` and strict ABAC filtering.
- Missing audit trails -> centralized audit service + request context + sensitive read logging + export/download audit.
- Lifecycle edits in views -> moved to workflow/lifecycle services with audited transitions.
- Cross-framework integrity gaps -> enforced model-level validation and `full_clean()` on save.
- Methodology versioning ambiguity -> linked indicators to MethodologyVersion and updated readiness.
- Alignment UI missing -> implemented alignment management pages and permissions.
- Export approval ambiguity -> InstanceExportApproval as sole authority; UI/logic updated.
- Limited API -> read-only, ABAC-safe registry endpoints.

## Authorization Evidence

**Code references**
- `src/nbms_app/services/authorization.py`: `is_system_admin()`, `filter_queryset_for_user()`
- `src/nbms_app/services/catalog_access.py`: SystemAdmin-only bypass
- `src/nbms_app/api.py`: audited reads via `audit_sensitive_access()`

**Tests**
- `src/nbms_app/tests/test_abac_views.py::test_staff_without_system_admin_cannot_view_iplc`
- `src/nbms_app/tests/test_abac_views.py::test_system_admin_can_view_restricted_and_iplc`
- `src/nbms_app/tests/test_authorization.py` (SystemAdmin behavior)

## Risk areas + mitigations
- Audit volume: sensitive reads logged per object; metadata redaction applied.
- Migration/backfill: additive migration + guarded backfill (only when exactly one active version exists).
- GDAL/PostGIS dependency: migration verification requires GDAL-enabled environment (documented in `docs/MIGRATION_VERIFICATION.md`).

## How to test

### Automated
```
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
$env:PYTHONPATH="$PWD\src"
pytest -q
```
Result: `219 passed, 14 warnings in 90.11s`

Warnings summary (pre-existing):
- 2x `RemovedInDjango60Warning` for `CheckConstraint.check` deprecation.
- 12x `RemovedInDjango60Warning` for default URL scheme change in `forms.URLField`.

### Manual smoke
- Verify SystemAdmin sees sensitive objects while non-admin staff do not.
- Exercise workflow transitions (submit/approve/publish/archive) and confirm audit logs.
- Validate export approvals and export downloads create audit events.
- Confirm alignment pages render and enforce permissions.
