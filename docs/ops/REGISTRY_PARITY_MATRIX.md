# Registry Parity Matrix

Purpose: track non-admin UI CRUD coverage for registry entities and highlight gaps.

## Scope

Entities: Framework, FrameworkGoal, FrameworkTarget, FrameworkIndicator, MonitoringProgramme, DatasetCatalog, Methodology, MethodologyVersion.

## Parity matrix (routes + gating)

| Entity | List route | Detail route | Create route | Edit route | Missing screens | Permissions/ABAC expectations |
| --- | --- | --- | --- | --- | --- | --- |
| Framework | `/frameworks/` (also `/catalog/frameworks/`) | `/frameworks/<uuid>/` | `/catalog/frameworks/new/` | `/catalog/frameworks/<uuid>/edit/` | None (archive exists at `/catalog/frameworks/<uuid>/archive/`) | List/detail filtered via `filter_queryset_for_user(..., perm=view_framework)`; create/edit/archive require catalog manager (ROLE_ADMIN or SystemAdmin). |
| FrameworkGoal | `/framework-goals/` (also `/catalog/framework-goals/`) | `/framework-goals/<uuid>/` | `/catalog/framework-goals/new/` | `/catalog/framework-goals/<uuid>/edit/` | None (archive exists at `/catalog/framework-goals/<uuid>/archive/`) | List/detail filtered with `filter_queryset_for_user` for ABAC; create/edit/archive require catalog manager. |
| FrameworkTarget | `/framework-targets/` (also `/catalog/framework-targets/`) | `/framework-targets/<uuid>/` | `/catalog/framework-targets/new/` | `/catalog/framework-targets/<uuid>/edit/` | None (archive exists at `/catalog/framework-targets/<uuid>/archive/`) | List/detail filtered via `filter_queryset_for_user(..., perm=view_frameworktarget)`; create/edit/archive require catalog manager. |
| FrameworkIndicator | `/framework-indicators/` (also `/catalog/framework-indicators/`) | `/framework-indicators/<uuid>/` | `/catalog/framework-indicators/new/` | `/catalog/framework-indicators/<uuid>/edit/` | None (archive exists at `/catalog/framework-indicators/<uuid>/archive/`) | List/detail filtered via `filter_queryset_for_user(..., perm=view_frameworkindicator)`; create/edit/archive require catalog manager. |
| MonitoringProgramme | `/catalog/monitoring-programmes/` | `/catalog/monitoring-programmes/<uuid>/` | `/catalog/monitoring-programmes/new/` | `/catalog/monitoring-programmes/<uuid>/edit/` | None | List/detail filtered via `filter_monitoring_programmes_for_user` + `audit_sensitive_access`; create requires contributor (Secretariat/Data Steward/Indicator Lead/Contributor) or SystemAdmin; edit requires `can_edit_monitoring_programme`. |
| DatasetCatalog | `/datasets/` | `/datasets/<uuid>/` | `/datasets/new/` | `/datasets/<uuid>/edit/` | None | List/detail filtered via `filter_dataset_catalog_for_user` + `audit_sensitive_access`; create requires contributor; edit requires `can_edit_dataset_catalog` (ABAC + ownership). |
| Methodology | `/catalog/methodologies/` | `/catalog/methodologies/<uuid>/` | `/catalog/methodologies/new/` | `/catalog/methodologies/<uuid>/edit/` | None | List/detail filtered via `filter_methodologies_for_user` + `audit_sensitive_access`; create requires contributor; edit requires `can_edit_methodology`. |
| MethodologyVersion | `/catalog/methodology-versions/` | `/catalog/methodology-versions/<uuid>/` | `/catalog/methodology-versions/new/` | `/catalog/methodology-versions/<uuid>/edit/` | None | List filtered via `filter_methodologies_for_user` + `audit_queryset_access`; detail uses `audit_sensitive_access`; create requires contributor; edit requires `can_edit_methodology` on parent and `audit_sensitive_access` on version. |

## Notes

- ABAC is enforced through `filter_queryset_for_user`/`filter_*_for_user` plus sensitivity checks. Consent gating does not apply to these registry entities (no IPLC consent workflow on these models).
- Archive actions are used instead of hard deletes for Framework/Goal/Target/Indicator.
