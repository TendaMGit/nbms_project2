# Demo Seed Plan (Phase 4)

This plan defines the deterministic demo seed workflow for NBMS Project 2.

## What the demo includes
- Organisations: SANBI (Org A), External Partner (Org B)
- Users:
  - `demo_admin` (staff, admin)
  - `demo_manager` (staff, alignment manager)
  - `demo_partner` (non-staff, Org B)
- Reporting cycle + instance (fixed UUIDs)
- Framework registry (GBF demo subset: goal/targets/indicators)
- National targets + indicators (one mapped + one unmapped each)
- Alignment mappings (partial to show orphans)
- Catalog entities:
  - MonitoringProgramme
  - Methodology + MethodologyVersion
  - DatasetCatalog
- Reporting data:
  - Dataset + DatasetRelease
  - Evidence (one IPLC-sensitive)
  - Indicator data series + points
  - Section III/IV progress entries
- Consent/IPLC example:
  - IPLC-sensitive evidence is approved but consent is missing by default

## Seed commands (Windows, no Docker)

Set the posture (PowerShell):
```
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:ENABLE_GIS='false'
$env:USE_REDIS='0'
$env:PYTHONPATH="$PWD\src"
```

Seed demo data (idempotent):
```
python manage.py demo_seed
```

Reset demo data (only demo-tagged objects):
```
python manage.py demo_seed --reset --confirm-reset
```

Seed in a "ready for export" state (approvals + consent granted):
```
python manage.py demo_seed --ready
```

## Expected blockers and how to resolve
Default seed leaves two blockers:
1) Pending approvals for one demo target + indicator
2) Missing consent for IPLC-sensitive evidence

Resolve via UI:
- Approvals: `/reporting/instances/<uuid>/approvals/`
- Consent: `/reporting/instances/<uuid>/consent/`

Or resolve via command (for verification/export):
```
python manage.py demo_verify --resolve-blockers
```

## Expected URLs (demo instance)
- Review dashboard: `/reporting/instances/<uuid>/review/`
- Alignment coverage: `/reporting/instances/<uuid>/alignment-coverage/`
- Orphan targets: `/reporting/instances/<uuid>/alignment/orphans/national-targets/`
- Orphan indicators: `/reporting/instances/<uuid>/alignment/orphans/indicators/`
- Approvals: `/reporting/instances/<uuid>/approvals/`
- Consent: `/reporting/instances/<uuid>/consent/`
- Review pack v2: `/reporting/instances/<uuid>/review-pack-v2/`

## Deterministic IDs
Key objects are created with fixed UUIDs and stable codes so repeated runs produce identical records.

## Verification
Run:
```
python manage.py demo_verify --resolve-blockers
```
This writes deterministic outputs to `docs/demo/golden/` and prints the export hash.

