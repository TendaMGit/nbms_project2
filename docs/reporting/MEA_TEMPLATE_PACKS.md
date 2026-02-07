# MEA_TEMPLATE_PACKS

## Purpose
NBMS now supports runtime template packs so additional MEA reporting structures can be added without rewriting core reporting workflows.

## Runtime Model
- `ReportTemplatePack` (`src/nbms_app/models.py`)
  - pack metadata (`code`, `mea_code`, `version`, `export_handler`)
- `ReportTemplatePackSection`
  - ordered section definitions with `schema_json`
- `ReportTemplatePackResponse`
  - per-instance response payloads tied to sections

## Current Packs
- `cbd_ort_nr7_v2` (primary)
- `ramsar_v1` (COP14-oriented runtime pack)
- `cites_v1` (scaffold)
- `cms_v1` (scaffold)

Seed command:
- `python manage.py seed_mea_template_packs`

## API Runtime
- List packs: `GET /api/template-packs`
- List sections: `GET /api/template-packs/{pack_code}/sections`
- Save/load responses:
  - `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/responses`
  - `POST /api/template-packs/{pack_code}/instances/{instance_uuid}/responses`
- Export:
  - `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/export`
- Validation:
  - `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/validate`
- PDF:
  - `GET /api/template-packs/{pack_code}/instances/{instance_uuid}/export.pdf`

## Ramsar Runtime Shape (`ramsar_v1`)
- `section_1_institutional`
  - reporting party and focal point details.
- `section_2_narrative`
  - wetland context, pressures, and policy updates.
- `section_3_implementation_indicators`
  - questionnaire rows with response + optional links to indicators/programmes/evidence.
- `section_4_annex_targets`
  - optional target alignment summary and linked code lists.

## Export Handler Plug-in
Registry:
- `src/nbms_app/services/template_pack_registry.py`

To add a new MEA exporter:
1. Add pack seed metadata in `seed_mea_template_packs.py`.
2. Implement exporter function in `template_pack_registry.py`.
3. Register handler name in `EXPORT_HANDLER_REGISTRY`.
4. Set `ReportTemplatePack.export_handler` to that key.
5. Add contract tests for output shape.

## ABAC and Scope Controls
- Pack APIs require authentication.
- Instance-scoped access enforced via `_require_instance_scope` in `src/nbms_app/api_spa.py`.
- Scope checks respect staff/admin constraints and instance-target scope behavior used in reporting exports.
- Unauthorized pack-instance access returns `403` and does not leak response payloads.
