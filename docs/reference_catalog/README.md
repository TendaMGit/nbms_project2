# Reference Catalog Inventory Pack (PR-1)

This directory contains the **Pilot Registry Inventory Pack** for the legacy
`nbms_project` prototype. It is a requirements and metadata source intended to
inform future registry rebuilds in `nbms_project2`.

**Important:** PR-1 is **docs/templates only**. No schema, migrations, endpoints,
or runtime behavior changes are included here.

## Who this is for

- Product owners and registry stewards defining reference data needs.
- Developers implementing the follow-on registry PRs.
- Data administrators preparing CSV imports.

## How to use this pack

1. Review `pilot_registry_inventory_pack.md` to see what existed in the pilot
   and where it appeared (models, admin, API, seed scripts, fixtures).
2. Use `target_model_plan.md` as the concrete implementation guide for the
   **future** registry PRs.
3. Use `controlled_vocabularies.md` and the CSV templates in `csv_templates/`
   to prepare seed data in a consistent, governance-safe format.

## What is *not* included

- PR-1 was docs/templates only; PR-2 introduces registry models and CSV tooling.
- No public API endpoints are added here (admin + management commands only).
- No pilot DB migration or legacy schema porting.

## Reference catalog imports/exports (PR-2+)

This repo now includes CSV import/export commands for the reference catalog
registry layer. These commands are **idempotent** and use UUIDs first, then
codes as the upsert key.

### Windows-first examples

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:PYTHONPATH=\"$PWD\\src\"

python manage.py reference_catalog_import --entity organisation --file docs\\reference_catalog\\csv_templates\\organisation_template.csv --mode upsert --dry-run
python manage.py reference_catalog_export --entity organisation --out .\\exports\\organisation_export.csv
```

### Import ordering (recommended)

1. organisation
2. sensitivity_class
3. data_agreement
4. monitoring_programme
5. dataset_catalog
6. methodology
7. methodology_version
8. programme_dataset_link
9. programme_indicator_link
10. methodology_dataset_link
11. methodology_indicator_link
12. gbf_goals
13. gbf_targets
14. gbf_indicators

### Identifier precedence and required columns

- If a UUID column is provided, it is used as the primary upsert key.
- If UUID is blank, the command uses the code column (e.g., org_code,
  dataset_code, programme_code).
- Required columns vary by entity; the importer validates that all template
  headers are present before processing rows.

## Readiness diagnostics

Use the readiness diagnostics command to assess catalog completeness for a
reporting instance and identify blockers for NR7 reporting readiness.

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
$env:PYTHONPATH="$PWD\src"

python manage.py reporting_readiness --instance <instance_uuid> --format json --scope selected
python manage.py reporting_readiness --instance <instance_uuid> --format csv --output .\\exports\\readiness.csv
```

Optional user-context checks:

```powershell
python manage.py reporting_readiness --instance <instance_uuid> --format json --scope selected --user <user_id_or_email>
python manage.py reporting_readiness --instance <instance_uuid> --format json --scope selected --org <org_code>
```

Release-mode checks (export governance context):

```powershell
python manage.py reporting_readiness --instance <instance_uuid> --format json --scope selected --mode release
```

Interpretation:
- `overall_ready` is true only when **no blocking gaps** exist.
- Missing methodology versions, dataset catalog links, or programme links are
  treated as blockers for indicator readiness.
- Consent and sensitivity checks surface as `CONSENT_REQUIRED` and
  `SENSITIVITY_BLOCKED` blockers where applicable.

Import ordering reminder:
Org -> Sensitivity -> Agreements -> Programmes/Datasets -> Methods -> Versions -> Links

## End-to-end demo walkthrough

Use the demo walkthrough to seed a small, idempotent dataset that exercises the
reference catalog registry layer and readiness diagnostics:

- `docs/reference_catalog/demo_walkthrough.md`
