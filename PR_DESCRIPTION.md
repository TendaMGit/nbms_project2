# PR: Phase 12 National Report Collaboration + Sign-Off + Dossier Integrity (on top of spatial/programme baseline)

## Phase 12 Increment Summary
This increment adds a production-style CBD National Report workspace (NR7/NR8 unified pack), multi-author revisioning/comments/suggestions, a defensible sign-off chain (including Technical Committee and Publishing Authority steps), print-ready exports (PDF + DOCX), and deterministic reporting dossiers with integrity manifests.

Primary additions:
- Unified pack/runtime:
  - `cbd_national_report_v1` template pack used for both NR7 and NR8 instances.
- Multi-author collaboration:
  - section revision chain (`ReportSectionRevision`)
  - comment threads/messages (`ReportCommentThread`, `ReportComment`)
  - suggestion workflow (`ReportSuggestedChange`)
- Sign-off chain:
  - workflow definitions/instances/actions/section approvals (`ReportWorkflow*`)
  - evidence gate before technical approval
  - lock/finalize behavior with final content hash
- Exports + dossier:
  - export artifacts (`ReportExportArtifact`)
  - dossier artifacts (`ReportDossierArtifact`)
  - deterministic ZIP bundle with integrity/audit/evidence manifests
- Angular National Report workspace:
  - section nav + schema-driven editor
  - comments/suggestions/history/workflow panels
  - export and dossier actions

## Phase 12 Commands Run
```powershell
docker compose --profile minimal up -d --build
docker compose --profile spatial up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend pytest -q
npm --prefix frontend run build
npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless
npm --prefix frontend run e2e

docker compose exec -e NBMS_ADMIN_USERNAME=Tenda -e NBMS_ADMIN_EMAIL=tmunyai56@gmail.com -e NBMS_ADMIN_PASSWORD=GraniteT33 backend python manage.py ensure_system_admin
docker compose exec -e SEED_DEMO_USERS=1 -e ALLOW_INSECURE_DEMO_PASSWORDS=1 backend python manage.py seed_demo_users
docker compose exec backend python manage.py seed_demo_reports
```

## Phase 12 Results
- Docker stacks: healthy (`minimal` and `spatial`)
- Migrations: `No migrations to apply`
- Backend tests: `401 passed`
- Frontend unit tests: `11 files, 12 tests passed`
- Playwright e2e: `3 passed`
- System admin ensured: `Tenda` with `SystemAdmin` group + superuser
- Demo users ensured: 17 seeded (idempotent)
- Demo reports ensured: NR7 + NR8 seeded

## Phase 11 Update (Registry Operationalization)
- Added workflow-governed registry transitions with evidence gates and audit logging:
  - `/api/registries/{object_type}/{object_uuid}/transition`
  - `/api/registries/{object_type}/{object_uuid}/evidence`
- Added registry gold marts and API:
  - `TaxonGoldSummary`, `EcosystemGoldSummary`, `IASGoldSummary`
  - `python manage.py refresh_registry_marts`
  - `GET /api/registries/gold`
- Added indicator registry readiness linkage:
  - `IndicatorRegistryCoverageRequirement`
  - indicator detail now returns `registry_readiness` + `used_by_graph`
- Added registry-consuming method SDK implementations:
  - `ecosystem_registry_summary`
  - `ias_registry_pressure_index`
  - `taxon_registry_native_voucher_ratio`
- Updated report products (NBA/GMO/Invasive) to include deterministic mart-derived `auto_sections`, citations, and evidence hooks.

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
- Backend tests (docker): `399 passed`.
- Backend tests (host): `398 passed, 1 skipped`.
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
