# ROLE VISIBILITY MATRIX (FOR LOCAL DEV/DEMO ONLY - DO NOT USE IN PRODUCTION)

Generated from code registries:
- `src/nbms_app/demo_users.py`
- `src/nbms_app/role_visibility.py`

## Surfaces

| label | route | capability | public |
|---|---|---|---|
| Dashboard | /dashboard | can_view_dashboard | no |
| Indicator Explorer | /indicators |  | yes |
| Spatial Viewer | /map | can_view_spatial | no |
| Programme Ops | /programmes | can_view_programmes | no |
| BIRDIE | /programmes/birdie | can_view_birdie | no |
| NR7 Builder | /nr7-builder | can_view_reporting_builder | no |
| MEA Packs | /template-packs | can_view_template_packs | no |
| Report Products | /report-products | can_view_report_products | no |
| System Health | /system-health | can_view_system_health | no |

## Role Matrix

| username | org | groups | staff? | superuser? | visible_routes |
|---|---|---|---|---|---|
| Contributor | SANBI | Contributor | yes | no | /dashboard; /indicators; /map |
| IndicatorLead | SANBI | Indicator Lead | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie |
| ProgrammeSteward | SAEON | Data Steward | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products |
| DatasetSteward | STATS-SA | Data Steward | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products |
| Reviewer | DFFE | Secretariat | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products |
| Approver | DFFE | Admin | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products; /system-health |
| Publisher | DFFE | Admin | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products; /system-health |
| RamsarFocalPoint | DFFE | Secretariat | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products |
| CITESFocalPoint | DFFE | Secretariat | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products |
| CMSFocalPoint | DFFE | Secretariat | yes | no | /dashboard; /indicators; /map; /programmes; /programmes/birdie; /nr7-builder; /template-packs; /report-products |
| Auditor | SANBI | Security Officer | yes | no | /dashboard; /indicators; /map |
| IPLCRepresentative | IPLC | Community Representative | yes | no | /dashboard; /indicators; /map |
| PublicUser | DEMOORG | Viewer | no | no | /dashboard; /indicators; /map |
