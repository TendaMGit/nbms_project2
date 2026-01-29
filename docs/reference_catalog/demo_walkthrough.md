# Demo Walkthrough (End-to-End Reference Catalog + Readiness)

This walkthrough creates a small, repeatable demo dataset using the reference
catalog CSV fixtures and the demo seed command. It is intended for local
testing and readiness regression checks.

## Prerequisites

- Apply migrations
- Create a superuser if you need admin access

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## Seed the demo (idempotent)

The demo seed uses the CSV fixtures in `docs/reference_catalog/demo_fixtures/`
and creates a minimal reporting cycle + instance, indicators, mappings, data
points, and consent records. It is safe to run more than once.

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:PYTHONPATH="$PWD\src"

python manage.py seed_end_to_end_demo --apply
```

To reset the demo data first:

```powershell
python manage.py seed_end_to_end_demo --reset --apply
```

To enforce readiness as a hard gate:

```powershell
python manage.py seed_end_to_end_demo --apply --strict
```

## Run readiness diagnostics

```powershell
python manage.py reporting_readiness --instance <instance_uuid> --format json --scope selected
```

Expected summary highlights:

- `overall_ready: true`
- `blocking_gap_count: 0`
- `total_indicators_in_scope >= 1`

## Editing the demo fixtures

All fixtures are under `docs/reference_catalog/demo_fixtures/`. Update the CSV
files in place and re-run the seed command. Use the same `source_system` and
`source_ref` values to keep the demo idempotent.

## Notes

- Demo records are tagged with `source_system=demo_seed` and `source_ref=demo_v1`.
- The seed command creates a demo org and user (`demo_admin`) if they do not exist.
