# PR: Spatial Programme + Overlay + E2E + Phase 10 Registries

## Summary
This PR includes the prior spatial/programme hardening stack and extends it with Phase 10 reference registries and programme templates.  
It adds ecosystem/taxon/IAS registry models, ingestion commands, ABAC-aware registry APIs, Angular registry explorers, and standards traceability docs.

## Commit Phases
1. `feat(spatial): harden source sync and ingest filtering`
   - Spatial ingest filters (country subset support), resilient source refresh fallback, schema/migration updates, and sync tests.
2. `feat(programmes): orchestrate spatial baselines runs with provenance`
   - Programme run command/orchestration, artefact+QA logging, geoserver publish hooks, overlay compute step, provenance linkage.
3. `feat(spatial-api): add indicator map endpoints and capability surface`
   - Indicator map endpoint + province aggregation support, API route additions, capability endpoint/service, API tests.
4. `feat(frontend): refine map workspace and indicator overlay views`
   - Map workspace AOI draw/legend upgrades, indicator detail multi-chart + map panel + pipeline metadata.
5. `feat(demo): add seeded role users and deterministic e2e auth sessions`
   - Demo/admin bootstrap commands, role visibility matrix export, deterministic session issuance for Playwright, e2e hardening.
6. `docs(spatial): publish pr-ready runbook/state/api matrix updates`
   - Runbook/API/integration/changelog/state updates and ADR.
7. `feat(registries): add standards-aligned ecosystem/taxon/ias registries`
   - Registry models/migration, enums, programme template model, and registry APIs.
8. `feat(registry-ingest): add vegmap/taxon/voucher/griis sync commands`
   - Ingestion and seed commands with provenance/idempotency.
9. `feat(frontend): add registry explorers and programme template page`
   - Angular routes/pages/service/models and capability-guarded navigation.
10. `test(registries): add API and command coverage`
    - Backend tests for filters/sensitivity and command idempotency.
11. `docs(registries): add standards trace and runbooks`
    - ADR, overview/runbook, external standards notes, and state/changelog/api/integration updates.

## Commands Run
```powershell
docker compose --profile spatial up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py sync_spatial_sources
docker compose exec backend python manage.py seed_geoserver_layers
docker compose exec backend python manage.py run_programme --programme-code NBMS-SPATIAL-BASELINES
docker compose exec backend pytest -q
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend run e2e
```

## Results
- Docker spatial stack: up/healthy.
- Backend tests (docker): `392 passed`.
- Backend tests (host): `391 passed, 1 skipped`.
- Frontend unit tests: `11 files, 12 tests passed`.
- Playwright e2e: `3 passed` (anonymous, system admin, role matrix visibility).

## Screenshot Checklist (to attach in PR)
- [ ] Map Workspace with layer catalog + AOI draw + legend
- [ ] Indicator detail showing trend + province bars + map panel
- [ ] Programme run detail showing QA + artefacts
- [ ] Role-based nav comparison (Contributor vs Reviewer vs PublicUser)
- [ ] Ecosystem registry explorer + detail tabs
- [ ] Taxon registry detail with sensitive locality redaction behavior
- [ ] IAS registry detail with EICAT/SEICAT panels
- [ ] GeoServer layer preview for published NBMS layer

## Risks & Mitigations
- Upstream source outages can fail refresh:
  - Mitigation: fallback keeps previous valid snapshot and marks sync as `skipped`.
- E2E auth flakiness across session rotation:
  - Mitigation: `issue_e2e_sessions` command + bootstrap flow; form-login fallback in tests.
- Access-surface drift with role changes:
  - Mitigation: centralized capabilities service + exported role visibility matrix + e2e role checks.
- External source variability in registry ingest:
  - Mitigation: idempotent command behavior, deterministic hashing, and stored source provenance.
