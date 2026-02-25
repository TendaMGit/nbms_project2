# Blueprint Alignment Report

Date: 2026-02-25  
Branch: `chore/align-blueprint-2026Q1`

## Summary of changes

- Enforced confidentiality handling for internal blueprint `.docx` files:
  - added explicit `.gitignore` entries.
  - verified files are not tracked and not present in history fast-pass scan.
- Added blueprint governance and scope documentation:
  - `BLUEPRINT_COMPLIANCE_CHECKLIST.md`
  - `ALIGNMENT_MATRIX.md`
  - `AUDIT_FINDINGS.md`
  - `VERIFICATION_PLAYBOOK.md`
- Implemented cross-entity discovery:
  - `GET /api/discovery/search` for indicators/targets/datasets.
  - Angular indicator explorer now exposes a cross-entity discovery panel.
- Implemented indicator release governance workflow:
  - new release workflow service with:
    - contributor attestation requirement,
    - ITSC-marked method prerequisite,
    - fast-path publish for non-sensitive releases,
    - steward queue for sensitive releases.
  - new endpoint: `POST /api/indicator-series/{series_uuid}/workflow`.
  - new attestation fields on `IndicatorDataSeries` + migration.
- Extended indicator status and readiness visibility:
  - API adds `next_expected_update_on`, `pipeline_maturity`, readiness status/score.
  - indicator detail UI now surfaces these fields plus release-workflow state.
  - dashboard API/UI now include readiness totals and per-target averages.
- Updated compute-framing language:
  - switched Section IV action wording from "recompute" to "refresh" in UI/docs.
  - added compatibility alias endpoint for legacy clients.
- Added docs guardrail in CI:
  - `scripts/check_blueprint_language.py`.
  - integrated into `Makefile` and GitHub Actions CI.
- Updated canonical docs to align with single-phase framing and governance boundaries.
- Fixed production image dependency gap for PDF/report stack:
  - root `Dockerfile` now installs `pkg-config` and `libcairo2-dev` in builder stage.
  - runtime stage includes `libcairo2`.

## Final quality gates (executed 2026-02-25)

- Backend tests: PASS (`422 passed, 1 skipped`).
- Backend checks: PASS (`manage.py check --settings=config.settings.dev`).
- Deploy check (prod settings with dummy env): PASS (warnings only).
- Predeploy check (prod settings with dummy env): PASS (warnings only).
- Frontend build: PASS.
- Frontend unit tests: PASS (`11 files, 12 tests`).
- E2E smoke: PASS (`3 passed`).
- Docker compose config render: PASS.
- Docker production image build: PASS.

Detailed command/output log:
- `docs/blueprint/VERIFICATION_OUTPUTS.md`

## Alignment matrix

- See: `docs/blueprint/ALIGNMENT_MATRIX.md`

## Major decisions

1. Kept legacy `/recompute-rollup` endpoint as compatibility alias while moving user-facing language to `refresh`.
2. Enforced ITSC release prerequisite through methodology version status + approval-body marker to avoid implicit approvals.
3. Applied single-phase wording (`Phase 1`) while retaining historical milestone context in archived runbook entries.

## Remaining P2 backlog

- Dedicated ITSC-only method approval transition API/UI (currently partial alignment).
- Expanded steward trigger set for explicit licence/embargo flags beyond sensitivity/IPLC fields.
- Angular-first goal/target page improvements for full FR-005 parity.
- Additional partner connectors beyond current BIRDIE baseline.

## Evidence pointers

Endpoints:
- `/api/discovery/search`
- `/api/indicator-series/{series_uuid}/workflow`
- `/api/reports/{uuid}/sections/section-iv/refresh-rollup`

Backend tests:
- `src/nbms_app/tests/test_indicator_release_workflow.py`
- `src/nbms_app/tests/test_api_indicator_explorer.py`

Frontend routes/pages:
- `/indicators` discovery panel + filters
- `/indicators/:uuid` status/readiness/release metadata
- `/dashboard` readiness dashboard panel

Docs:
- `docs/blueprint/VERIFICATION_PLAYBOOK.md`
- `docs/blueprint/AUDIT_FINDINGS.md`
- `docs/blueprint/VERIFICATION_OUTPUTS.md`
