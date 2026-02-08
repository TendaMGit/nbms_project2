# PR: Spatial Programme + Overlay + E2E (PR-ready commit series)

## Summary
This PR repackages the working spatial/programme increment into a phase-separated, reviewable commit stack without changing product behavior.  
It hardens spatial source ingest, operationalizes programme-run provenance, exposes indicator spatial map endpoints, refines Angular map/indicator UX, and makes demo-role e2e auth deterministic.

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

## Commands Run
```powershell
docker compose --profile spatial up -d --build
docker compose exec backend pytest -q
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend run e2e
```

## Results
- Docker spatial stack: up/healthy.
- Backend tests: `382 passed`.
- Frontend unit tests: `8 passed`.
- Playwright e2e: `3 passed` (anonymous, system admin, role matrix visibility).

## Screenshot Checklist (to attach in PR)
- [ ] Map Workspace with layer catalog + AOI draw + legend
- [ ] Indicator detail showing trend + province bars + map panel
- [ ] Programme run detail showing QA + artefacts
- [ ] Role-based nav comparison (Contributor vs Reviewer vs PublicUser)
- [ ] GeoServer layer preview for published NBMS layer

## Risks & Mitigations
- Upstream source outages can fail refresh:
  - Mitigation: fallback keeps previous valid snapshot and marks sync as `skipped`.
- E2E auth flakiness across session rotation:
  - Mitigation: `issue_e2e_sessions` command + bootstrap flow; form-login fallback in tests.
- Access-surface drift with role changes:
  - Mitigation: centralized capabilities service + exported role visibility matrix + e2e role checks.
