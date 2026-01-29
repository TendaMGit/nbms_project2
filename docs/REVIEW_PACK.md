# Security + Governance Integrity Pack - Review Pack

## Scope
- ABAC hardening to remove staff bypass; SystemAdmin defined as the only unrestricted role.
- Audit trail expansion (request metadata, CRUD signals, sensitive read audits, export/download audits).
- Lifecycle transitions routed through service layer (archive-only; no view-layer status writes).
- Cross-framework referential integrity enforced at model level.
- FrameworkGoal lifecycle aligned with the rest of the catalog.
- MethodologyVersion-first linkage for indicators + readiness logic updates.
- Alignment UI for national?framework targets/indicators and methodology versions.
- Read-only API endpoints for registry entities with ABAC + audited reads.

## Key Decisions
- SystemAdmin = superuser OR group "SystemAdmin" OR permission `nbms_app.system_admin`.
- Staff users do not bypass ABAC.
- Archive-only policy enforced in site + admin.
- Indicator?Methodology links resolve to an active MethodologyVersion.

## Files Changed (high level)
- `src/nbms_app/models.py`, `src/nbms_app/services/*`, `src/nbms_app/views.py`, `src/nbms_app/admin.py`
- `src/nbms_app/api.py`, `src/nbms_app/forms.py`, `src/nbms_app/forms_catalog.py`
- `src/nbms_app/signals_audit.py`, `src/nbms_app/middleware_audit.py`
- `src/nbms_app/migrations/0026_alter_user_options_auditevent_content_type_and_more.py`
- `src/nbms_app/tests/*` (role + methodology version updates)
- `docs/SECURITY_GOVERNANCE_NOTES.md`, `docs/migrations/0026_security_governance_integrity.md`, `docs/API.md`
- `docs/AUDIT_EVENTS.md`, `docs/AUDIT_QUERIES.md`, `docs/MIGRATION_VERIFICATION.md`, `PR_DESCRIPTION.md`
- `docker-compose.verify.yml`, `docker/verify/Dockerfile`, `.env.verify.example`
- `scripts/verify_migrations.ps1`, `scripts/verify_migrations.sh`
- `.github/workflows/migration-verify.yml`

## How to Test (Windows)
- `$env:DJANGO_SETTINGS_MODULE='config.settings.test'`
- `$env:PYTHONPATH="$PWD\src"`
- `pytest`

## Reference Docs
- `docs/AUDIT_EVENTS.md` (audit taxonomy + metadata)
- `docs/AUDIT_QUERIES.md` (example audit queries)
- `docs/MIGRATION_VERIFICATION.md` (migration verification log)

## Addendum: Post-merge hardening
- Merged internal review dashboard branch with main to resolve compatibility drift.
- Added AuditEvent indexes and purge command for operational safety.
- Cleaned deprecation warnings (CheckConstraint and URLField scheme).
