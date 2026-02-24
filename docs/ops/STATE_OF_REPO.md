# STATE OF REPO - NBMS Project 2

## PHASE 12 NATIONAL REPORT COLLAB + SIGN-OFF + DOSSIER VERIFIED (2026-02-09)
- Branch: `feat/national-report-collab-signoff-v1`
- Scope: unified NR7/NR8 workspace, multi-author revisions/comments/suggestions, sign-off chain, PDF/DOCX/JSON exports, dossier integrity pack, and internal/public gating.

Commands executed (docker, required set):
- `docker compose --profile minimal up -d --build` -> pass (backend/frontend/postgis/redis/minio healthy)
- `docker compose --profile spatial up -d --build` -> pass (GeoServer profile healthy)
- `docker compose exec backend python manage.py migrate` -> `No migrations to apply`
- `docker compose exec backend pytest -q` -> `401 passed` (warnings only)

Commands executed (frontend, required set):
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless` -> `11 files, 12 tests passed`
- `npm --prefix frontend run e2e` -> `3 passed`
  - note: updated stale selector `NR7 Builder` to `National Report` in Playwright smoke specs.

Identity + demo data verification:
- `docker compose exec -e NBMS_ADMIN_USERNAME=admin_user -e NBMS_ADMIN_EMAIL=admin@example.org -e NBMS_ADMIN_PASSWORD=CHANGE_ME backend python manage.py ensure_system_admin`
  -> `System admin updated: username=Tenda, staff=True, superuser=True, group=SystemAdmin`
- `docker compose exec -e SEED_DEMO_USERS=1 -e ALLOW_INSECURE_DEMO_PASSWORDS=1 backend python manage.py seed_demo_users`
  -> `Seeded demo users (17 rows)`, wrote `docs/ops/DEMO_USERS.md`
- `docker compose exec backend python manage.py seed_demo_reports`
  -> `Seeded demo report instances for NR7/NR8 (2 instances).`

Phase outcomes:
- New report workspace APIs operational under `/api/reports/{uuid}/*` for:
  - sections/history/comments/suggestions
  - workflow/status transitions
  - PDF/DOCX/JSON exports
  - dossier generation and retrieval
- Dossier includes deterministic integrity files:
  - `submission.json`, `report.pdf`, `report.docx`, `evidence_manifest.json`, `audit_log.json`, `integrity.json`, `visibility.json`
- Internal report access controls are enforced for preview/export/dossier endpoints.

## PHASE 11 REGISTRY WORKFLOWS + MARTS + INDICATOR/REPORT INTEGRATION VERIFIED (2026-02-08)
- Branch: `feat/phase10-registries-programmes`
- Scope: registry approval/evidence workflows, gold summary marts, registry-derived indicator methods/readiness, and report-product auto-populated sections.

Commands executed (host):
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations nbms_app` -> created migration `0039_ecosystemgoldsummary_iasgoldsummary_and_more`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `398 passed, 1 skipped`
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless` -> `11 files, 12 tests passed`
- `npm --prefix frontend run e2e` -> `3 passed`

Commands executed (docker, validation set):
- `docker compose --profile spatial up -d --build` -> pass (backend/frontend/postgis/geoserver/minio/redis healthy)
- `docker compose exec backend python manage.py migrate` -> `No migrations to apply`
- `docker compose exec backend pytest -q` -> `399 passed`
- Runtime probes:
  - `GET /health/` -> `200`
  - `GET /health/storage/` -> `200`

Phase outcomes:
- New API surface operational:
  - `/api/registries/gold`
  - `/api/registries/{object_type}/{object_uuid}/evidence`
  - `/api/registries/{object_type}/{object_uuid}/transition`
- Registry transitions now evidence-gated and audited.
- Indicator detail payload now includes:
  - `registry_readiness`
  - `used_by_graph`
- Report product payload now includes deterministic `auto_sections` + `citations` + `evidence_hooks`.

## PHASE 10 REGISTRIES + PROGRAMME TEMPLATES VERIFIED (2026-02-08)
- Branch: `feat/phase10-registries-programmes`
- Scope: standards-aligned ecosystem/taxon/IAS registries, programme template catalog, Angular registry explorers, ABAC-sensitive locality masking, and role visibility updates.

Commands executed (host):
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `391 passed, 1 skipped`
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless` -> `11 files, 12 tests passed`
- `npm --prefix frontend run e2e` -> `3 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py export_role_visibility_matrix` -> wrote updated markdown+csv

Commands executed (docker, required set):
- `docker compose --profile spatial up -d --build` -> pass (backend/frontend/postgis/geoserver/minio/redis healthy)
- `docker compose exec backend python manage.py migrate` -> `No migrations to apply`
- `docker compose exec backend python manage.py sync_spatial_sources` -> `ready=0, skipped=3, blocked=0, failed=0`
- `docker compose exec backend python manage.py seed_geoserver_layers` -> `published=6, skipped=0`
- `docker compose exec backend python manage.py run_programme --programme-code NBMS-SPATIAL-BASELINES` -> `status=succeeded`, run uuid `9822158c-e208-4d9b-b08e-b853a3e299f4`
- `docker compose exec backend pytest -q` -> `392 passed`

Phase outcome:
- Registry APIs available:
  - `/api/registries/ecosystems*`
  - `/api/registries/taxa*`
  - `/api/registries/ias*`
  - `/api/programmes/templates`
- Sensitive voucher locality redaction verified in API behavior and tests.
- Role visibility matrix now includes registry and programme-template surfaces.

## PR-READY REBASE (2026-02-08)
- Branch: `feat/spatial-programme-overlay-e2e-prready`
- Source baseline: `feat/spatial-real-data-programmes-v1` (starting from `759b414` + working-tree hardening set)
- Commit series grouped by phase:
  - `feat(spatial): harden source sync and ingest filtering`
  - `feat(programmes): orchestrate spatial baselines runs with provenance`
  - `feat(spatial-api): add indicator map endpoints and capability surface`
  - `feat(frontend): refine map workspace and indicator overlay views`
  - `feat(demo): add seeded role users and deterministic e2e auth sessions`
  - `docs(spatial): publish pr-ready runbook/state/api matrix updates` (this docs commit)

Validation commands executed:
- `docker compose --profile spatial up -d --build` -> pass
- `docker compose exec backend pytest -q` -> `382 passed, 45 warnings`
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless` -> `8 passed`
- `npm --prefix frontend run e2e` -> `3 passed` (anonymous + system admin + role-matrix smoke)

## PHASE 8 OPERATIONAL STABILITY + ROLE E2E VERIFIED (2026-02-08)
- Branch: `feat/spatial-real-data-programmes-v1`
- Scope: stabilized authenticated e2e, added deterministic session bootstrap command, hardened spatial source refresh fallback, refreshed role-visibility artefacts.

Commands executed (docker):
- `docker compose --profile spatial up -d --build` -> pass (backend/frontend/geoserver healthy)
- `docker compose exec backend python manage.py migrate` -> `No migrations to apply`
- `docker compose exec backend python manage.py sync_spatial_sources` -> `ready=0, skipped=3, blocked=0, failed=0`
- `docker compose exec backend python manage.py run_programme --programme-code NBMS-SPATIAL-BASELINES` -> `status=succeeded`
- `docker compose exec backend python manage.py seed_geoserver_layers` -> `published=6, skipped=0`
- `docker compose exec backend python manage.py verify_geoserver_smoke` -> pass (`checked_layers=6`)
- `docker compose exec backend pytest -q` -> `381 passed, 45 warnings`
- `docker compose exec backend python manage.py export_role_visibility_matrix` -> wrote markdown + CSV artefacts

Commands executed (frontend):
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless` -> `8 passed`
- `npm --prefix frontend run e2e` -> `3 passed` (anonymous + system admin + role visibility matrix)

Operational notes:
- Added backend command `issue_e2e_sessions` and switched Playwright bootstrap to use it.
- Spatial sync now retains prior valid snapshot (`skipped`) when source refresh fails transiently.
- Role visibility docs exported to:
  - `docs/ops/ROLE_VISIBILITY_MATRIX.md`
  - `docs/ops/ROLE_VISIBILITY_MATRIX.csv`
- Layer feature counts (PostGIS check):
  - `ZA_PROVINCES_NE=51`
  - `ZA_PROTECTED_AREAS_NE=1626`
  - `ZA_ECOSYSTEM_PROXY_NE=12`
- Runtime endpoint probes:
  - `GET /api/ogc/collections` -> `200`
  - `GET /api/tiles/ZA_PROVINCES_NE/0/0/0.pbf` -> `200`

## PHASE 8 SPATIAL REAL-DATA + PROGRAMME OPS VERIFIED (2026-02-08)
- Branch: `feat/spatial-real-data-programmes-v1`
- Scope: real-source spatial sync, GeoServer publication verification, map/auth UX hardening, Docker reproducibility re-check.

Commands executed (docker, mandatory set):
- `docker compose --profile minimal up -d --build` -> pass (backend/frontend/core healthy)
- `docker compose --profile spatial up -d --build` -> pass (GeoServer profile healthy)
- `docker compose exec backend python manage.py migrate` -> `No migrations to apply`
- `docker compose exec backend python manage.py sync_spatial_sources` -> `ready=0, skipped=3, blocked=0, failed=0` (idempotent checksum skip)
- `docker compose exec backend python manage.py seed_geoserver_layers` -> `published=6, skipped=0`
- `docker compose exec backend python manage.py verify_geoserver_smoke` -> pass (`checked_layers=6`)
- `docker compose exec backend pytest -q` -> `367 passed, 21 warnings`

Commands executed (frontend):
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test` -> `8 passed`
- `npm --prefix frontend run e2e` -> `1 passed, 1 skipped` (authenticated smoke skipped when `PLAYWRIGHT_*` credentials not set)

Real-source ingest verification:
- `docker compose exec backend python manage.py sync_spatial_sources --source-code NE_PROTECTED_LANDS_ZA --force` -> `rows_ingested=1626` from DFFE SAPAD public feed.
- Source registry checks:
  - `NE_ADMIN1_ZA` feature count: `51`
  - `NE_PROTECTED_LANDS_ZA` feature count: `1626`
  - `NE_GEOREGIONS_ZA` feature count: `12`

Runtime checks:
- `GET /health/` via backend -> `{"status":"ok"}`
- `GET /api/ogc/collections` -> `200`, `collections=6`
- `GET /api/tiles/ZA_PROVINCES_NE/0/0/0.pbf` -> `200`, `application/vnd.mapbox-vector-tile`
- `GET http://127.0.0.1:8081/` -> `200` (Angular shell served)
- GeoServer smoke includes WMS capabilities + map request verification for published NBMS layers.

## SPATIAL REGISTRY + OGC VERIFIED (2026-02-07)
- Branch: `feat/demo-users-systemadmin-v1` (working tree for spatial increment)
- Scope: full spatial hardening pass (registry models, OGC APIs, vector tiles, GeoServer publish, Docker reproducibility, idempotent seed fixes)

Commands executed (host):
- `python --version` -> `Python 3.13.4`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `366 passed, 1 skipped`
- `npm --prefix frontend run build` -> pass
- `npm --prefix frontend run test -- --watch=false --browsers=ChromeHeadless` -> `8 passed`
- `$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:8081'; $env:PLAYWRIGHT_USERNAME='ciadmin'; $env:PLAYWRIGHT_PASSWORD='CI_Admin_12345'; npm --prefix frontend run e2e` -> `2 passed` (anonymous + authenticated smoke)

Commands executed (docker):
- `docker compose --profile minimal up -d --build` -> pass (backend/frontend/core healthy)
- `docker compose --profile spatial up -d --build` -> pass (GeoServer profile healthy)
- `docker compose exec backend python manage.py migrate` -> `No migrations to apply`
- `docker compose exec backend pytest -q` -> `367 passed, 18 warnings`
- `docker compose exec backend python manage.py seed_demo_spatial` -> `created=0` (idempotent rerun)
- `docker compose exec backend python manage.py seed_geoserver_layers` -> `published=3, skipped=0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_migrations.ps1` -> PASS (`366 passed, 1 skipped` in verify stack)

Runtime checks:
- `GET /health/` -> `{"status":"ok"}`
- `GET /health/storage/` -> `{"status":"ok"}`
- `GET /api/ogc/collections` -> `collections 3`
- `GET /api/tiles/ZA_PROVINCES/tilejson` -> valid tilejson payload
- `GET /api/tiles/ZA_PROVINCES/0/0/0.pbf` -> `200`
- Frontend root `http://localhost:8081/` -> `200 OK`
- `GET /account/login/` content check -> two-factor template warning absent (`two_factor/_base.html` active)
- CSRF login through nginx proxy verified with trusted origins including `http://localhost:8081` and `http://127.0.0.1:8081`

Key hardening notes:
- Spatial migration compatibility fixed for non-GDAL environments (`0035` now uses GIS-safe wrappers).
- Spatial seed commands are idempotent against legacy slug/code states.
- GeoServer publish command is idempotent on reruns (handles pre-existing feature type responses).
- Backend docker image now includes dev test dependencies, so `docker compose exec backend pytest -q` is first-class.

## DEMO USERS + SYSTEMADMIN VERIFIED (2026-02-07)
- Branch: `feat/demo-users-systemadmin-v1`
- Runtime baseline reference: `docs/MIGRATION_VERIFICATION.md` (canonical verify path)

Commands executed (host):
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `361 passed, 16 warnings`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.dev"; python manage.py ensure_system_admin` (with `NBMS_ADMIN_*`) -> `System admin updated: username=Tenda, staff=True, superuser=True`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.dev"; python manage.py seed_demo_users` (with `SEED_DEMO_USERS=1`, `ALLOW_INSECURE_DEMO_PASSWORDS=1`) -> demo matrix seeded and `docs/ops/DEMO_USERS.md` written
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.dev"; python manage.py list_demo_users` -> expected role pack listed

Commands executed (docker minimal):
- `docker compose --profile minimal up -d --build` (with `SEED_DEMO_USERS=1`, `ALLOW_INSECURE_DEMO_PASSWORDS=1`, `NBMS_ADMIN_*`) -> backend/frontend/core services healthy
- `curl http://127.0.0.1:8000/health/` -> `{"status": "ok"}`
- `curl http://127.0.0.1:8081/health/` -> `{"status": "ok"}`
- `docker compose exec -T backend python manage.py list_demo_users` -> seeded role matrix present in container
- `docker compose exec -T backend python manage.py shell -c "<auth checks>"` ->
  - `admin_auth True`
  - `admin_page 200`
  - `indicatorlead_api 200`
  - `public_draft_count 0`
- Login flow probe via frontend proxy:
  - POST `/account/login/?next=/dashboard` with `Tenda` credentials -> final URI `http://127.0.0.1:8081/dashboard`
  - authenticated `GET /admin/` -> `200`
- `curl http://127.0.0.1:8081/account/login/` content check -> two-factor template warning absent
- `docker compose exec backend python manage.py ensure_system_admin` (with `NBMS_ADMIN_USERNAME=admin_user`) -> updated in-container system admin; `authenticate(username='admin_user', password='CHANGE_ME') -> True`

Migration verification (canonical):
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_migrations.ps1` -> PASS
- Results:
  - verification image built from current `docker/verify/Dockerfile`
  - migrations apply cleanly
  - `python manage.py check` clean
  - docker test run `361 passed`
  - `python manage.py verify_post_migration` passed

## One Biodiversity Hardening V1 - Phases 4-7 Completion Slice (2026-02-07)
- Branch: `feat/one-biodiversity-hardening-v1`
- Working baseline advanced from uncommitted Phase 4 state to integrated hardening slice.

Commands executed (host):
- `python --version` -> `Python 3.13.4`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `352 passed`
- `$env:PYTHONPATH="$PWD\src"; python manage.py check` -> no issues
- `$env:PYTHONPATH="$PWD\src"; python manage.py makemigrations nbms_app` -> created `0034_birdiesite_birdiespecies_integrationdataasset_and_more`
- `$env:PYTHONPATH="$PWD\src"; python manage.py makemigrations --check --dry-run` -> no changes detected
- `$env:PYTHONPATH="$PWD\src"; python manage.py migrate` -> applied `0034`
- `$env:PYTHONPATH="$PWD\src"; python manage.py seed_gbf_indicators` -> seeded `13` headline + `22` binary GBF indicators
- `$env:PYTHONPATH="$PWD\src"; python manage.py seed_mea_template_packs` -> seeded `4` packs, `15` sections
- `$env:PYTHONPATH="$PWD\src"; python manage.py seed_birdie_integration` -> ingested BIRDIE snapshot (`species=4, sites=3, abundance=9, occupancy=3, wcv=3`)
- `$env:PYTHONPATH="$PWD\src"; python manage.py seed_report_products` -> seeded `nba_v1`, `gmo_v1`, `invasive_v1`

Commands executed (frontend local):
- `npm --prefix frontend install` -> updated lockfile and installed Playwright dependency
- `npm --prefix frontend run test` -> `7 files, 8 tests passed`
- `npm --prefix frontend run build` -> pass
- `npx --prefix frontend playwright install chromium` -> browser installed
- `npm --prefix frontend run e2e` -> `1 passed`

Commands executed (docker minimal):
- `docker compose --profile minimal up -d --build` -> backend/frontend/core services healthy
- `docker compose ps` -> backend/frontend/postgis/redis/minio healthy
- `curl.exe http://127.0.0.1:8000/health/` -> `{"status": "ok"}`
- `curl.exe http://127.0.0.1:8081/health/` -> `{"status": "ok"}`
- `curl.exe http://127.0.0.1:8081/` -> Angular shell served (`NBMS Workspace`)

Implemented in this slice:
- Phase 4:
  - Completed GBF catalog readiness with `IndicatorMethodProfile`, `IndicatorMethodRun`, method SDK, and APIs.
- Phase 5:
  - Hardened Ramsar pack with COP14-style sections, QA endpoint, deterministic exporter, and PDF export.
  - Added interactive Angular template-pack editor with section QA workflow.
- Phase 6:
  - Implemented BIRDIE connector module and ingestion command with bronze/silver/gold lineage persistence.
  - Added BIRDIE dashboard API and Angular dashboard page with site/species/provenance panels.
- Phase 7:
  - Added report product framework for NBA/GMO/Invasive shells with HTML/PDF export endpoints and Angular workspace.
  - Added Playwright smoke e2e for docker-served frontend.

ADRs added:
- `docs/adr/0008-gbf-indicator-catalog-import-strategy.md`
- `docs/adr/0009-birdie-integration-connector-pattern.md`
- `docs/adr/0010-report-product-framework.md`

## One Biodiversity Hardening V1 - Phase 3 Programme Ops (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Base commit for phase: `14bbbff`

Commands executed (host):
- `python --version` -> `Python 3.13.4`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations nbms_app` -> created `0032_monitoringprogramme_data_quality_rules_json_and_more`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q src/nbms_app/tests/test_api_programme_ops.py src/nbms_app/tests/test_programme_ops_commands.py` -> `7 passed`
- `npm --prefix frontend run test` -> `4 files, 5 tests passed`
- `npm --prefix frontend run build` -> pass
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `344 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py migrate` -> applied `0031` and `0032` on host DB
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py seed_programme_ops_v1` -> seeded NBMS core + BIRDIE integration programmes
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py run_monitoring_programmes --limit 5` -> command executed (0 due runs)

Commands executed (docker):
- `docker compose --profile minimal up -d --build` -> backend/frontend/core services healthy
- `curl.exe http://127.0.0.1:8000/health/` -> `{"status":"ok"}`
- `curl.exe http://127.0.0.1:8081/health/` -> `{"status":"ok"}`
- `curl.exe -I http://127.0.0.1:8081/programmes` -> `HTTP/1.1 200 OK`

Implemented in phase:
- Added monitoring programme operations runtime models and migration (`MonitoringProgrammeSteward`, `MonitoringProgrammeRun`, `MonitoringProgrammeRunStep`, `MonitoringProgrammeAlert`).
- Added programme ops service runner + queue (`src/nbms_app/services/programme_ops.py`).
- Added programme ops API endpoints and ABAC steward-aware filtering.
- Added Angular Programme Ops page with run-now/dry-run controls and run/alert panels.
- Added seed + scheduler commands (`seed_programme_ops_v1`, `run_monitoring_programmes`).
- Added ADR `docs/adr/0007-programme-job-runner-lineage-model.md`.

## One Biodiversity Hardening V1 - Phase 0 Baseline (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Base branch/commit: `feat/ui-spatial-indicators-v1` @ `cc22263`

Commands executed (host):
- `python --version` -> `Python 3.13.4`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `324 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py check` -> no issues
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations --check --dry-run` -> no changes detected

Commands executed (docker):
- `docker compose --profile minimal up -d --build` -> backend/frontend/core services started
- `docker compose --profile minimal ps` -> backend/frontend/postgis/redis/minio healthy
- `Invoke-WebRequest http://127.0.0.1:8000/health/` -> `{"status": "ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/` -> `200`
- `Invoke-WebRequest http://127.0.0.1:8081/health/` -> `{"status": "ok"}`

Baseline status:
- Host baseline: PASS
- Docker baseline: PASS
- Proceeding to Phase 1 hardening

## One Biodiversity Hardening V1 - Phase 1 Hardening (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Commit base for phase: `cc22263`

Commands executed:
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q src/nbms_app/tests/test_request_id.py src/nbms_app/tests/test_rate_limiting.py src/nbms_app/tests/test_api_system_health.py src/nbms_app/tests/test_session_security.py src/nbms_app/tests/test_prod_settings.py src/nbms_app/tests/test_api_spa_auth.py src/nbms_app/tests/test_audit_transition_coverage.py` -> `16 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `334 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py check` -> no issues
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations --check --dry-run` -> no changes detected
- `npm --prefix frontend run test` -> `2 passed`
- `npm --prefix frontend run build` -> pass
- `docker compose --profile minimal up -d --build` -> pass
- `Invoke-WebRequest http://127.0.0.1:8000/health/` -> `{"status":"ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/health/` -> `{"status":"ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/api/help/sections` -> `200`

Implemented in phase:
- Request-ID middleware and log correlation.
- CSP/security header middleware and production defaults.
- Session fixation mitigation (single rekey after auth).
- Expanded rate limits (exports/public API/metrics).
- System health API + Angular page.
- CI security additions: Bandit + Trivy.
- Backup/restore helper scripts and runbook.

## One Biodiversity Hardening V1 - Phase 2 NR7 Builder Uplift (2026-02-06)
- Branch: `feat/one-biodiversity-hardening-v1`
- Base commit for phase: `7f533d8`

Commands executed:
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q src/nbms_app/tests/test_api_nr7_builder.py src/nbms_app/tests/test_api_spa_auth.py src/nbms_app/tests/test_request_id.py` -> `9 passed`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q` -> `337 passed`
- `npm --prefix frontend run test` -> `4 passed`
- `npm --prefix frontend run build` -> pass
- `docker compose --profile minimal up -d --build` -> pass
- `Invoke-WebRequest http://127.0.0.1:8000/health/` -> `{"status":"ok"}`
- `Invoke-WebRequest http://127.0.0.1:8081/health/` -> `{"status":"ok"}`

Implemented in phase:
- Added NR7 builder APIs for instance listing, QA/preview summary, and PDF export.
- Added validation engine for required fields, cross-section checks, and readiness integration.
- Added Angular NR7 Report Builder page with QA bar, section completion list, live preview, and PDF action.
- Added richer section-help payload (`sections_rich`) for contextual guidance.
- Added PDF runtime dependencies to backend Docker image and requirements.

## UI/Spatial/Indicator Increment Verification (2026-02-06)
- Branch: `feat/ui-spatial-indicators-v1`
- Base commit at start of increment: `db98d16`

Commands executed (host):
- `python --version`
- `python -m pip install -r requirements.txt`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; pytest -q`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py check`
- `$env:PYTHONPATH="$PWD\src"; $env:DJANGO_SETTINGS_MODULE="config.settings.test"; python manage.py makemigrations --check --dry-run`
- `cd frontend; npm run build`
- `cd frontend; npm run test`
- `docker compose --profile minimal up -d --build`
- `docker compose --profile full up -d`
- `docker compose --profile minimal ps`
- `Invoke-WebRequest http://127.0.0.1:8000/health/`
- `Invoke-WebRequest http://127.0.0.1:8081/health/`
- `Invoke-WebRequest http://127.0.0.1:8081/api/help/sections`
- `Invoke-WebRequest http://127.0.0.1:8081/api/indicators?status=published`
- `Invoke-WebRequest http://127.0.0.1:8081/api/spatial/layers`

Result summary:
- Backend test suite: `324 passed`
- Django checks: clean (`No changes detected` for migrations)
- Frontend: Angular build passes; frontend tests pass (`2 passed`)
- Docker minimal profile: backend + frontend + PostGIS + Redis + MinIO healthy
- Docker full profile: starts GeoServer on `http://127.0.0.1:8080/`
- Health checks:
  - backend direct `/health/` -> `{"status": "ok"}`
  - frontend-proxied `/health/` -> `{"status": "ok"}`
- API checks:
  - `/api/help/sections` status `200`
  - `/api/indicators?status=published` returns seeded GBF workflow indicators
  - `/api/spatial/layers` returns seeded map layer metadata

## BASELINE VERIFIED (2026-02-06)
- Branch: `feat/nr7-full-conformance-integration`
- Commands executed (Windows host):
  - `git status`
  - `git branch`
  - `python --version`
  - `python -m pip install -r requirements.txt`
  - `python -m pip install -r requirements-dev.txt`
  - `$env:DJANGO_SETTINGS_MODULE='config.settings.test'; $env:PYTHONPATH="$PWD\src"; pytest -q`
  - `python manage.py check`
  - `python manage.py migrate`
  - `python manage.py runserver`
  - health checks: `GET /health/`, `GET /health/storage/`
- Result summary:
  - local suite: `308 passed`
  - `check` and `migrate` succeeded
  - `/health/` returned `{"status":"ok"}`
  - `/health/storage/` returned `{"status":"disabled","detail":"USE_S3=0"}`
- Docker baseline:
  - `docker compose -f docker/docker-compose.yml up -d` verified after fixing `minio-init` image tag to `minio/mc:latest`.

## Snapshot scope
- Audited commit (main): `d4efd3f8d7cf6b9a7fea98586c40ee54f44e9559`
- Captured at: 2026-01-30 10:17 (local) before docs branch `feat/docs-repo-state`
- Verified: `git log -1 main` matched the audited commit at capture time
- Included: code and docs on `main` at the audited commit
- Excluded: docs-only edits on this branch, unmerged feature branches, and local stashes
- Authoritative docs note: This file is the authoritative Windows-first runbook unless superseded

## A. Repo metadata
- Repo root: `C:\Users\T.Munyai\OneDrive\Apps\NMSI\About GBF development_Draft for prep\nbms_project2`
- Git status (captured before docs branch): `## main...origin/main`
- HEAD commit (captured before docs branch): `d4efd3f8d7cf6b9a7fea98586c40ee54f44e9559`
- Branch (captured before docs branch): `main`
- Python: `3.13.4`
- Django: `5.2.9`
- Pip top-level (from `python -m pip list --not-required`):
  - `boto3==1.34.162`
  - `celery==5.4.0`
  - `dj-database-url==2.2.0`
  - `django-filter==24.3`
  - `django-geojson==4.2.0`
  - `django-guardian==2.4.0`
  - `django-leaflet==0.33.0`
  - `django-storages==1.14.3`
  - `django-two-factor-auth==1.17.0`
  - `drf-spectacular==0.28.0`
  - `drf-spectacular-sidecar==2024.7.1`
  - `openpyxl==3.1.5`
  - `pdfplumber==0.11.9`
  - `phonenumbers==8.13.40`
  - `pip-tools==7.5.2`
  - `playwright==1.52.0`
  - `psycopg2-binary==2.9.10`
  - `Pygments==2.19.2`
  - `pytest-django==4.10.0`
  - `python-docx==1.2.0`
  - `python-dotenv==1.0.1`
  - `redis==5.0.8`
  - `xhtml2pdf==0.2.17`

## B. Features inventory

| Feature | Status (main/branch) | Primary files | Routes/Commands | Gating summary | Tests |
| --- | --- | --- | --- | --- | --- |
| ORT NR7 export v2 (`nbms.ort.nr7.v2`) + strict gating + deterministic output | main (merged from `feat/ort-nr7-export-v2`) | `src/nbms_app/exports/ort_nr7_v2.py`<br>`src/nbms_app/services/exports.py`<br>`src/nbms_app/services/section_progress.py`<br>`src/nbms_app/services/indicator_data.py`<br>`src/nbms_app/views.py`<br>`src/nbms_app/urls.py`<br>`docs/exports/ort_nr7_v2_export.md` | `/exports/instances/<uuid>/ort-nr7-v2.json` (option `?download=1`) | `assert_instance_exportable` enforces readiness + approvals; `_require_referential_integrity` blocks unapproved/ABAC/consent-violating references; scoped targets via `scoped_national_targets`/`scoped_framework_targets`; deterministic ordering via stable JSON + sorted lists | `src/nbms_app/tests/test_ort_nr7_v2_export.py` |
| Internal review dashboard + Review Pack v2 | main (branch `feat/internal-review-dashboard` has unmerged commits) | `src/nbms_app/views.py`<br>`src/nbms_app/services/review.py`<br>`src/nbms_app/services/review_decisions.py`<br>`templates/nbms_app/reporting/review_dashboard.html`<br>`templates/nbms_app/reporting/review_pack_v2.html` | `/reporting/instances/<uuid>/review/`<br>`/reporting/instances/<uuid>/review-pack-v2/`<br>`/reporting/instances/<uuid>/review-decisions/` | Staff-only + instance ABAC via `_require_section_progress_access`; strict user proxy removes staff bypass; consent filters applied to evidence/releases; scoped targets and approved items only | `src/nbms_app/tests/test_review_dashboard.py`<br>`src/nbms_app/tests/test_review_decisions.py` |
| Structured Section III/IV progress models + instance-scoped ABAC + frozen POST blocking | main (merged from `feat/section-iii-iv-structured-storage`) | `src/nbms_app/models.py` (SectionIII/IV)<br>`src/nbms_app/services/section_progress.py`<br>`src/nbms_app/forms.py`<br>`src/nbms_app/views.py`<br>`templates/nbms_app/reporting/section_iii_*`<br>`templates/nbms_app/reporting/section_iv_*` | `/reporting/instances/<uuid>/section-iii/`<br>`/reporting/instances/<uuid>/section-iv/` | `_require_section_progress_access` enforces instance-scoped approvals + ABAC; `scoped_national_targets`/`scoped_framework_targets` filter visibility; frozen instances set read-only and block POST unless admin override | `src/nbms_app/tests/test_section_progress.py`<br>`src/nbms_app/tests/test_reporting_freeze.py` |
| Alignment framework registries + mapping tables (Framework/Goal/Target/Indicator + link models) | main (merged from multiple `feat/*` branches) | `src/nbms_app/models.py` (Framework*, link models)<br>`src/nbms_app/services/alignment.py`<br>`src/nbms_app/views.py`<br>`src/nbms_app/forms_catalog.py`<br>`src/nbms_app/migrations/0017_*`<br>`src/nbms_app/migrations/0022_*`<br>`src/nbms_app/migrations/0026_*` | `/frameworks/`, `/framework-targets/`, `/framework-indicators/`<br>`/catalog/frameworks/`, `/catalog/framework-goals/`, `/catalog/framework-targets/`, `/catalog/framework-indicators/`<br>`python manage.py import_alignment_mappings` / `export_alignment_mappings` | ABAC via `filter_queryset_for_user`; catalog manager required for CRUD; link filters enforce `is_active` and ABAC on both sides; cross-framework integrity validated | `src/nbms_app/tests/test_alignment_mappings.py`<br>`src/nbms_app/tests/test_cross_framework_integrity.py` |
| Indicator data series/points + binary indicator questions/responses + ABAC+consent filters | main (merged from `feat/indicator-and-binary-data-models`) | `src/nbms_app/models.py` (IndicatorDataSeries/Point, BinaryIndicatorQuestion/Response)<br>`src/nbms_app/services/indicator_data.py`<br>`src/nbms_app/management/commands/seed_binary_indicator_questions.py`<br>`src/nbms_app/management/commands/import_indicator_data.py`<br>`src/nbms_app/management/commands/export_indicator_data.py` | `python manage.py seed_binary_indicator_questions`<br>`python manage.py import_indicator_data`<br>`python manage.py export_indicator_data` | ABAC via `filter_queryset_for_user`; consent filter applied to IPLC-sensitive series/questions; points limited by allowed series and dataset releases | `src/nbms_app/tests/test_indicator_data.py` |
| Reporting snapshots + diff (Phase 6A) | main (merged from `feat/reporting-snapshots-diff`) | `src/nbms_app/models.py` (ReportingSnapshot)<br>`src/nbms_app/services/snapshots.py`<br>`src/nbms_app/views.py`<br>`templates/nbms_app/reporting/snapshots_list.html`<br>`templates/nbms_app/reporting/snapshot_detail.html`<br>`templates/nbms_app/reporting/snapshot_diff.html` | `/reporting/instances/<uuid>/snapshots/`<br>`/reporting/instances/<uuid>/snapshots/create/`<br>`/reporting/instances/<uuid>/snapshots/diff/` | Snapshot creation uses ORT NR7 v2 export gating (readiness + approvals) with strict user proxy; views require staff + instance ABAC; snapshots are immutable and deduped by payload hash | `src/nbms_app/tests/test_reporting_snapshots.py` |

## C. Domain model summary (entities + key relationships)
- Core identity + ABAC (0001, 0004): `User`, `Organisation`, plus lifecycle/sensitivity fields and ABAC scaffolding in `src/nbms_app/models.py`.
- Reporting core (0011-0016): `ReportingCycle` -> `ReportingInstance`; `InstanceExportApproval` (content_type + object_uuid + scope); `ExportPackage`; `ConsentRecord`; `ReportSectionTemplate`/`ReportSectionResponse`; `ValidationRuleSet`.
- Catalog + evidence/data (0009-0010, 0025-0026): `Dataset`, `DatasetRelease`, `Evidence`, `License`, `SourceDocument` plus QA/metadata fields.
- Alignment registry (0017, 0022, 0026): `Framework` -> `FrameworkGoal` -> `FrameworkTarget` -> `FrameworkIndicator`; mapping tables `NationalTargetFrameworkTargetLink` and `IndicatorFrameworkIndicatorLink`.
- Indicator data + binary questions (0018): `IndicatorDataSeries` (exclusive FK to `Indicator` or `FrameworkIndicator`) -> `IndicatorDataPoint` (optional `DatasetRelease`); `BinaryIndicatorQuestion` -> `BinaryIndicatorResponse` (per `ReportingInstance`).
- Structured progress (0019): `SectionIIINationalTargetProgress` (ReportingInstance + NationalTarget) and `SectionIVFrameworkTargetProgress` (ReportingInstance + FrameworkTarget), each with M2M links to series, binary responses, evidence, and dataset releases.
- Snapshots + review decisions (0020-0023): `ReportingSnapshot` (immutable, hash-deduped) and `ReviewDecision` (immutable, tied to snapshot).
- Reference catalog expansions (0022-0024): `SensitivityClass`, `DataAgreement`, `DatasetCatalog`, `MonitoringProgramme`, `Methodology` + `MethodologyVersion`, and link tables for dataset/indicator/methodology/programme relationships.

## D. Workflows summary
- ReportingInstance lifecycle: `ReportingStatus` supports `draft -> pending_review -> approved -> released -> archived` in `src/nbms_app/models.py`. In practice, gating is enforced via approvals, readiness checks, snapshots, and review decisions rather than explicit status transitions.
- Freeze/override: `reporting_instance_freeze` sets `frozen_at`/`frozen_by` (`src/nbms_app/views.py`); non-admin edits and approvals are blocked while frozen; admin override allowed for approvals and unfreeze.
- Instance-scoped approvals: `InstanceExportApproval` is keyed by content type + object UUID + scope; `approved_queryset` powers readiness, review summaries, and exports (`src/nbms_app/services/instance_approvals.py`).
- Consent/IPLC gating: `requires_consent` + `ConsentRecord` (instance-specific or global) enforce IPLC-sensitive visibility; approvals and exports block without consent; indicator data filters apply consent gating (`src/nbms_app/services/consent.py`, `src/nbms_app/services/indicator_data.py`).
- Export gating: `assert_instance_exportable` enforces readiness + approvals; ORT NR7 v2 export also enforces referential integrity across referenced series/evidence/releases; `EXPORT_REQUIRE_SECTIONS` and `EXPORT_REQUIRE_READINESS` can hard-block exports (`src/nbms_app/services/exports.py`, `src/nbms_app/exports/ort_nr7_v2.py`).

## E. Local development runbook (Windows, no Docker, ENABLE_GIS=false)
Assumptions:
- Postgres is running locally.
- `DATABASE_URL` points to `nbms_project2_db` (or set NBMS_* vars instead).
- GIS disabled: `ENABLE_GIS=false` (avoids GDAL/GEOS on Windows).

### 1) Postgres provisioning (psql)
Run once as a Postgres superuser:
```
# Update these values for your environment
$env:PGHOST='localhost'
$env:PGPORT='5432'
$env:PGUSER='postgres'

psql -d postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='nbms_user') THEN CREATE ROLE nbms_user LOGIN PASSWORD 'YOUR_PASSWORD'; END IF; END $$;"
psql -d postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname='nbms_project2_db') THEN CREATE DATABASE nbms_project2_db OWNER nbms_user; END IF; END $$;"
```

### 2) App setup and run (PowerShell)
```
# from repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Copy-Item .env.example .env

# Local session env (or place in .env)
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:DJANGO_DEBUG='true'
$env:ENABLE_GIS='false'
$env:DATABASE_URL='postgresql://nbms_user:YOUR_PASSWORD@localhost:5432/nbms_project2_db'
$env:USE_S3='0'

python manage.py migrate
python manage.py bootstrap_roles
python manage.py seed_reporting_defaults
python manage.py runserver
```

### 3) Known-good smoke verification
Start the server (if not already running):
```
python manage.py runserver
```

In a second PowerShell:
```
Invoke-WebRequest http://127.0.0.1:8000/health/ | Select-Object -Expand Content
Invoke-WebRequest http://127.0.0.1:8000/health/storage/ | Select-Object -Expand Content
```
Expected responses:
- `/health/` -> `{ "status": "ok" }` (DB reachable)
- `/health/storage/` with `USE_S3=0` -> `{ "status": "disabled", "detail": "USE_S3=0" }`

### Troubleshooting
- OneDrive file locks: symptoms include sporadic migration failures or file-in-use errors. Move the repo to `C:\dev\nbms_project2` to avoid sync locks.
- psycopg2 connection errors: verify `DATABASE_URL` or `NBMS_DB_NAME`, `NBMS_DB_USER`, `NBMS_DB_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`. Ensure `ENABLE_GIS=false` and no GIS-only engine is forced.
- Migrations/roles missing: run `python manage.py migrate` and `python manage.py bootstrap_roles` before first login.

GIS dependency note:
- `ENABLE_GIS` controls whether `django.contrib.gis` is installed and whether a GIS engine is used (`src/config/settings/base.py`).
- When `ENABLE_GIS=false`, the engine is forced to `django.db.backends.postgresql`, which avoids GDAL/GEOS setup on Windows.

## F. Tests and health
- Pytest (Windows):
```
$env:DJANGO_SETTINGS_MODULE='config.settings.test'
$env:PYTHONPATH="$PWD\src"
pytest -q
```
- Targeted tests (examples):
```
pytest -q src/nbms_app/tests/test_ort_nr7_v2_export.py
pytest -q src/nbms_app/tests/test_review_dashboard.py
pytest -q src/nbms_app/tests/test_section_progress.py
```
- Health endpoints:
  - `/health/` returns `{ "status": "ok" }` if DB is reachable; otherwise 503.
  - `/health/storage/` returns `{ "status": "disabled", "detail": "USE_S3=0" }` when local storage is used; otherwise checks S3.
- Consistent warnings: no repo-documented warnings found; `scripts/test.sh` runs with `PYTHONWARNINGS=default` to surface deprecations if they appear.

## G. Branch/PR status & pending work
- Local branches (merged into main): `feat/alignment-mapping-tables`, `feat/catalog-admin-parity`, `feat/catalog-vocab-provenance`, `feat/framework-registry-crud`, `feat/gbf-preload-alignment`, `feat/indicator-and-binary-data-models`, `feat/ort-export-v1-narrative`, `feat/ort-nr7-export-v2`, `feat/phase6-domain-exports`, `feat/reporting-snapshots-diff`, `feat/review-signoff-decisions`, `feat/section-iii-iv-structured-storage`, `feat/security-governance-integrity-pack`.
- Local branches not merged (as of 2026-01-30): `feat/alignment-integration-ui`, `feat/db-schema-docs`, `feat/docs-repo-state`, `feat/docs-repo-state-polish`, `feat/framework-goals`, `feat/internal-review-dashboard`, `feat/ort-export-v1`, `feat/ort-template-conformance`, `feat/post-merge-hardening`, `feat/windows-infra-doctor`, `rescue/local-state-20260115`.
- Phase 6A snapshots/diff: merged into `main` (branch `feat/reporting-snapshots-diff` is in merged list).
- Stashes (names only):
  - `stash@{0}`: WIP before switching to main (file lock fix)
  - `stash@{1}`: wip alignment integration fixes
  - `stash@{2}`: phase5-review
  - `stash@{3}`: phase4c+phase5

### Unmerged branches triage
Merge status is from a dry-run `git merge --no-commit --no-ff main` into each branch on 2026-01-30 (no commits).

| Branch name | Last commit date | Touches migrations? | Touches auth/ABAC/consent/export gating? | Touches templates/UI only? | Merge status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `feat/alignment-integration-ui` | 2026-01-27 | Y | Y | N | Conflicts | Large cross-cutting alignment UI + governance changes; conflicts in models/views/templates. |
| `feat/db-schema-docs` | 2026-01-28 | Y | Y | N | Clean | Docs-heavy branch with governance changes; verify before merge. |
| `feat/docs-repo-state` | 2026-01-30 | N | N | N | Clean | Docs-only repo state capture (superseded by polish branch). |
| `feat/docs-repo-state-polish` | 2026-01-30 | N | N | N | Clean | Docs-only polish (current work). |
| `feat/framework-goals` | 2026-01-27 | Y | Y | N | Conflicts | FrameworkGoal lifecycle/index migration plus governance touches. |
| `feat/internal-review-dashboard` | 2026-01-29 | N | N | N | Clean | No diff vs main; candidate for cleanup. |
| `feat/ort-export-v1` | 2026-01-16 | Y | Y | N | Conflicts | Legacy ORT export + catalog work; heavy overlap with main. |
| `feat/ort-template-conformance` | 2026-01-20 | Y | Y | N | Conflicts | ORT conformance/docs + code changes; conflicts in core files. |
| `feat/post-merge-hardening` | 2026-01-29 | Y | Y | N | Clean | Audit hardening + migration 0027; review scope before merge. |
| `feat/windows-infra-doctor` | 2026-01-29 | Y | Y | N | Clean | Windows infra doctor scripts + migration 0027; review scope. |
| `rescue/local-state-20260115` | 2026-01-15 | Y | Y | N | Conflicts | Rescue snapshot; not intended for merge. |

Notes:
- "Touches auth/ABAC/consent/export gating" is flagged when a branch changes `src/nbms_app/exports/*`, `services/authorization.py`, `services/consent.py`, `services/exports.py`, `services/instance_approvals.py`, or `models.py`.
- "Touches templates/UI only" is true only when all changes are under `templates/` or `static/`.

## H. Known risks / tech debt
- OneDrive file locks: repo lives under OneDrive; sync can lock SQLite or migration files. Recommended dev location: `C:\dev\nbms_project2` (avoid sync, reduce file lock and path-length issues).
- GIS/GDAL portability: enabling GIS on Windows requires GDAL/GEOS paths; keep `ENABLE_GIS=false` unless GIS is required.
- Keep README and `docs/ops/STATE_OF_REPO.md` in sync; treat this file as the authoritative runbook.
- Local `.env` exists but is ignored by git; keep secrets out of the repo and rotate if ever committed.
