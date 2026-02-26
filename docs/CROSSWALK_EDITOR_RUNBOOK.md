# CROSSWALK EDITOR RUNBOOK

## Scope
This runbook covers VegMap to IUCN GET mapping and RLE-ready assessment curation in NBMS.

## Preconditions
- Docker spatial runtime is up:
  - `docker compose --profile spatial up -d --build`
- Backend migrations applied:
  - `docker compose exec backend python manage.py migrate`

## 1) Seed GET Reference Hierarchy
Run once (idempotent):
```bash
docker compose exec backend python manage.py seed_get_reference
```

Result:
- Populates `IucnGetNode` records used by crosswalk dropdowns and API detail views.

## 2) Ingest VegMap Baseline
Command:
```bash
docker compose exec backend python manage.py sync_vegmap_baseline
```

Modes:
- Online mode (default): uses configured source URL if available.
- Offline mode: pass an uploaded local file path (shp/gpkg/geojson) when direct online pull is unavailable.

Output:
- Creates/updates `EcosystemType`.
- Creates placeholder `EcosystemTypologyCrosswalk` rows with `review_status=needs_review`.
- Stores provenance (`source_system`, `source_ref`, checksums where available).

## 3) Review and Curate Crosswalks
Primary API read surface:
- `GET /api/registries/ecosystems`
- `GET /api/registries/ecosystems/{uuid}`

Review workflow fields per crosswalk:
- `confidence` (0-100)
- `review_status` (`needs_review`, `in_review`, `approved`, `rejected`)
- `is_primary`
- `evidence`
- `reviewed_by`, `reviewed_at`

Operational policy:
- Do not auto-map beyond trivial realm-level defaults.
- All production mappings require review approval.

## 4) Add RLE-ready Assessments
Populate `EcosystemRiskAssessment` rows with:
- `assessment_year`
- `assessment_scope`
- `category` (`CR`, `EN`, `VU`, `NT`, `LC`, `DD`, `NE`, `CO`)
- `criterion_a` .. `criterion_e`
- `evidence`
- reviewer workflow fields

These records are exposed through ecosystem detail API payloads.

## 5) QA Checks
Minimum QA for each ingest/review cycle:
- Every active ecosystem has at least one crosswalk row.
- Every primary crosswalk has evidence and reviewer metadata.
- No unresolved duplicate primaries for the same ecosystem/version.
- Risk assessment category aligns with supplied criteria text.

## 6) Suggested Operational Sequence
1. Run `sync_vegmap_baseline`.
2. Review and update crosswalk confidence/status.
3. Capture or update RLE-ready assessment rows.
4. Re-run programme pipeline:
   - `python manage.py run_programme --programme-code NBMS-PROG-ECOSYSTEMS`
5. Export/update readiness views for dependent indicators.

## 7) Security Notes
- Registry endpoints are authenticated.
- ABAC applies to ecosystem records and related assessments.
- Sensitive locality controls apply to specimen vouchers, not ecosystem polygons.
