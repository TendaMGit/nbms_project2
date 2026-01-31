# Pilot Import Script Plan (docs-only)

This plan describes how Phase 3.1 import scripts should be implemented. It is **docs-only** and does not change application behavior.

## Source extraction options (Windows-friendly)

### Option A: psql COPY / \copy (recommended)
Pros:
- Fast, deterministic, easy to automate.
- Works well for large tables.
Cons:
- Requires direct DB access and stable SQL views for complex joins.

Example (PowerShell):
```
$env:PGHOST='localhost'
$env:PGPORT='5432'
$env:PGUSER='postgres'

psql -d nbms_project_db -c "\copy (select * from nbms_app_nationaltarget) to 'C:\\temp\\national_targets.csv' csv header"
```

### Option B: Django dumpdata
Pros:
- Uses Django ORM; easier for complex relationships.
Cons:
- JSON output is larger; transformation required; ordering may be less deterministic.

Example:
```
python manage.py dumpdata nbms_app.NationalTarget --output C:\temp\national_targets.json
```

### Option C: Custom SQL views
Pros:
- Allows normalization and consistent key generation at source.
Cons:
- Requires DB schema knowledge; versioned views must be managed.

## Target import options (nbms_project2)

### Existing commands to reuse
- Registry/catalog:
  - `python manage.py reference_catalog_export`
  - `python manage.py reference_catalog_import`
- Alignment mappings:
  - `python manage.py export_alignment_mappings`
  - `python manage.py import_alignment_mappings`
- Indicator data:
  - `python manage.py export_indicator_data`
  - `python manage.py import_indicator_data`
- Binary indicator questions (seed, do not extract):
  - `python manage.py seed_binary_indicator_questions`

### Commands missing (planned)
- `import_national_targets` (CSV/JSON) with ABAC + consent defaults
- `import_indicators` (CSV/JSON) with deterministic national_target resolution
- `import_datasets_releases` (if DatasetCatalog + DatasetRelease cannot be covered by reference_catalog_import)
- `import_evidence` (if Evidence is required for pilot)

Each new command should support:
- `--dry-run`
- `--strict`
- deterministic ordering
- structured error reporting (row number + column)

## Recommended run order
1) Framework registry + controlled vocabularies
2) National targets
3) Indicators
4) Alignment mappings
5) Catalog entities (programmes, datasets, releases, methodologies)
6) Indicator data series/points
7) (Optional) instance-scoped progress/approvals

## Logging + audit expectations
- Write an import log per run: `logs/import_<timestamp>.log`
- Write a validation report per run: `logs/validation_<timestamp>.txt`
- Persist the ID mapping ledger: `migration_id_map.csv`
- Include counts for created/updated/skipped/failed rows.

## Windows-first conventions
- Use absolute paths in scripts (`C:\\temp\\...`).
- Avoid reliance on bash or Docker.
- Set `ENABLE_GIS=false` during imports.

