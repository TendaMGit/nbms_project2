# NBMS Report Template Inventory (Current)

Source of truth: `src/nbms_app/management/commands/seed_report_templates.py`

## ReportSectionTemplate fields

NBMS currently stores:
- code (string, unique)
- title
- ordering
- schema_json (required flag + fields list)
- is_active

There is no explicit report type, framework, or version field on the template model.

## Seeded templates (current)

All templates are seeded with `is_active = True` and `schema_json.required = True`.

| Code | Title | Ordering | Required fields (schema_json.fields) |
| --- | --- | --- | --- |
| section-i | Section I: Status of biodiversity | 1 | summary (required), key_trends, challenges |
| section-ii | Section II: Implementation measures | 2 | policy_measures (required), financing, capacity_building |
| section-iii | Section III: National targets progress | 3 | progress_overview (required), indicator_highlights |
| section-iv | Section IV: Support needed | 4 | support_needs (required), support_received |
| section-v | Section V: Additional information | 5 | annex_notes, references |

## How templates are referenced in readiness/export

- Readiness uses `ValidationRuleSet.rules_json.sections.required`, normalizes codes via
  `nbms_app.services.readiness._normalize_section_code`, and expects templates with
  `code` matching `section-i`..`section-v`.
- Views for section edit/preview resolve templates by `code`.
- Export packaging pulls active templates ordered by `ordering, code`.

## Observations

- No Annex/Other-Information template exists yet.
- No template metadata for NR7/NR8/framework selection is available in the model.
