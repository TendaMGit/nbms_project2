# Security + Governance Notes

## Summary (this PR)
- Defined SystemAdmin as: superuser OR group "SystemAdmin" OR permission `nbms_app.system_admin`; removed staff-based ABAC bypasses.
- ABAC filtering now consistently treats staff as normal users unless SystemAdmin; catalog access uses the same rule.
- Audit trail expanded:
  - `AuditEvent` now records event_type, content_type/object_id, and request metadata (path, method, IP, UA, session/request IDs).
  - Request context middleware captures request context for audit logs and admin change views.
  - Signals now audit create/update/delete for all `nbms_app` models (excluding `AuditEvent`).
  - Audit metadata is sanitized to redact sensitive fields (geometry, narrative text, contact details, payloads).
  - Sensitive reads are audited in detail views, admin change views, API reads, and key list views.
  - Export/downloads and snapshot views/diffs are audited.
- Lifecycle integrity:
  - Archive/unarchive actions now go through `lifecycle_service` (no direct status/is_active writes in views).
  - Admin delete is disabled; archive actions use the service layer.
- Cross-framework integrity enforced at model level:
  - FrameworkTarget.goal and FrameworkIndicator.framework_target must belong to the same framework.
  - `save()` calls `full_clean()` to enforce integrity across admin/import/ORM paths.
- FrameworkGoal lifecycle aligned with catalog pattern (status/sensitivity/org/created_by); `is_active` derived from status.
- MethodologyVersion-first linkage:
  - New `IndicatorMethodologyVersionLink` model.
  - Readiness diagnostics now require active methodology versions.
  - Import/export updated to map indicator?methodology links to active versions, with migration backfill.
- NationalTarget/Indicator metadata expanded to match reference catalog specification; forms/templates updated.
- Alignment UI added for national?framework targets/indicators and indicator?methodology version links.
- Read-only API endpoints added for framework + registry entities with ABAC filtering and audited reads.
- Export approvals unified: `export_approved` is read-only; InstanceExportApproval remains the sole approval source.

## Roles + Access Rules (operational summary)
- SystemAdmin: unrestricted access; all sensitive access is audited.
- Staff: no implicit ABAC bypass.
- Catalog management: Admin role (or SystemAdmin).
- Approvals: Data Steward / Secretariat / Admin (or SystemAdmin).

## How to verify
- Windows:
  - `$env:DJANGO_SETTINGS_MODULE='config.settings.test'`
  - `$env:PYTHONPATH="$PWD\src"`
  - `pytest`
