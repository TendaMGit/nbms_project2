# Blueprint Verification Playbook

## Scope
Use this checklist to verify that NBMS aligns with the revised blueprint for `Phase 1 - National MVP`.

Latest execution evidence:
- `docs/blueprint/VERIFICATION_OUTPUTS.md`

## Prerequisites
- Backend dependencies installed.
- Frontend dependencies installed (`frontend/package-lock.json`).
- `.env` configured for local/dev run.
- Migration state up to date.

## Command set

Backend:
```powershell
$env:PYTHONPATH="$PWD\src"
$env:DJANGO_SETTINGS_MODULE="config.settings.test"
python manage.py migrate
pytest -q
python manage.py check --settings=config.settings.dev
```

Frontend:
```powershell
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
```

Docker config validation:
```powershell
docker compose -f docker-compose.prod.yml config
```

## Seed commands (demo/runtime)

```powershell
$env:PYTHONPATH="$PWD\src"
python manage.py seed_reporting_defaults
python manage.py seed_mea_template_packs
python manage.py seed_gbf_indicators
python manage.py seed_indicator_workflow_v1
python manage.py seed_birdie_integration
```

## FR smoke checklist

FR-001/FR-002 search + discovery:
- `GET /api/discovery/search?search=forest`
- Expect indicator/target/dataset counts > 0 with demo seed.
- Anonymous calls must not expose restricted records.

FR-003 dashboard:
- `GET /api/dashboard/summary` as authenticated user.
- Confirm `indicator_readiness.totals` and `indicator_readiness.by_target` are present.

FR-004/FR-015 indicator status tracking:
- `GET /api/indicators/{uuid}`
- Confirm `next_expected_update_on`, `pipeline_maturity`, `readiness_status`, `readiness_score`.

FR-006/FR-007 reporting + template packs:
- Open `/reporting` Angular workspace.
- Generate Section III skeleton, refresh Section IV rollup, export PDF/DOCX/JSON.
- Validate template packs via `/api/template-packs/{pack}/instances/{uuid}/validate`.

FR-008 downloads/exports:
- Confirm public export download succeeds for authorized package.
- Confirm restricted/sensitive exports are denied without approvals/consent.
- Validate spatial GeoJSON export with ABAC:
  - `GET /api/spatial/layers/{layer_code}/export.geojson`

FR-011/FR-013/FR-014 sensitive release workflow:
- Submit non-sensitive indicator series release with attestation:
  - `POST /api/indicator-series/{series_uuid}/workflow` body `{ "action": "submit", "sense_check_attested": true }`
  - Expect status `published` (fast path).
- Submit restricted/IPLC series release:
  - Expect status `pending_review`.
- Steward approval:
  - `POST /api/indicator-series/{series_uuid}/workflow` body `{ "action": "approve" }`
  - Expect status `published`.

FR-012 ITSC method prerequisite:
- Attempt submission where linked methodology version is not ITSC-marked active.
- Expect `400` with ITSC approval requirement message.

FR-016 partner integration contract baseline:
- Run partner integration command:
  - `python manage.py run_monitoring_programmes --programme-code NBMS-BIRDIE-INTEGRATION`
- Confirm run record, QA result, and lineage data persisted.

FR-017 audit logging:
- Query `AuditEvent` entries for release/workflow actions:
  - `indicator_release_submit`
  - `indicator_release_publish_fast_path`
  - `indicator_release_steward_approve`

## Access control verification

- Anonymous user:
  - can read public indicators/search only.
  - cannot access authenticated endpoints (`/api/programmes*`, `/api/template-packs*`).
- Contributor user (same org):
  - can submit own indicator release.
- Data Steward/Admin user:
  - can approve pending sensitive release in same org.
- Cross-org user:
  - must not approve another org's sensitive release.

## Reporting export verification

- For a seeded reporting instance:
  - `GET /api/reports/{uuid}/export.pdf`
  - `GET /api/reports/{uuid}/export.docx`
  - `GET /api/reports/{uuid}/export`
  - `POST /api/reports/{uuid}/dossier`
- Confirm artifacts are generated and retrievable.
