# Registry CSV templates (Phase 1)

This doc describes the CSV templates and import/export commands for the registry/catalog entities in Phase 1.

## Commands

Export data (current records):

```
python manage.py reference_catalog_export --entity <entity> --out <path>
```

Export a template with headers + example row:

```
python manage.py reference_catalog_export --entity <entity> --out docs/import_export/templates/<entity>.csv --template
```

Import with validation (default upsert):

```
python manage.py reference_catalog_import --entity <entity> --file <path> --mode upsert
```

Dry-run (validate without writing):

```
python manage.py reference_catalog_import --entity <entity> --file <path> --dry-run
```

Strict mode (fail on first error):

```
python manage.py reference_catalog_import --entity <entity> --file <path> --strict
```

## Phase 1 entities

- framework
- framework_goal
- framework_target
- framework_indicator
- monitoring_programme
- dataset_catalog
- methodology
- methodology_version

Templates live in `docs/import_export/templates/`.

## Required columns (minimum)

- framework: `framework_code`, `title`
- framework_goal: `framework_code`, `goal_code`, `goal_title`
- framework_target: `framework_code`, `target_code`, `target_title` (goal_code optional)
- framework_indicator: `framework_code`, `indicator_code`, `indicator_title` (framework_target_code optional)
- monitoring_programme: `programme_code`, `title`
- dataset_catalog: `dataset_code`, `title`, `custodian_org_code`, `access_level`
- methodology: `methodology_code`, `title`
- methodology_version: `methodology_code`, `version`

## Foreign key resolution

- Organisation references use `org_code` (for example `organisation_code`, `custodian_org_code`, `lead_org_code`).
- Framework references use `framework_code`.
- Methodology version references use `methodology_code` and `version`.
- Link tables allow UUIDs if provided; otherwise codes are used.

## Validation error examples

- `Row 2: Organisation not found for code 'ORG-X'.`
- `Row 3: Invalid access_level 'invalid'.`
- `Row 5: framework_code and title are required.`

## Notes

- Default mode is `upsert` (update-or-create). Use `insert_only` to prevent updates.
- `--dry-run` wraps the import in a transaction and rolls back changes.
- Template example rows are minimal; fill in additional optional fields as needed.
