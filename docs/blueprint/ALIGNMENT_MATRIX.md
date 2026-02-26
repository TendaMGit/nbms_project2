# Alignment Matrix

Status legend:
- `PASS`: implemented and evidenced in code + tests/docs.
- `PARTIAL`: implementation exists but governance depth or rollout remains incomplete.
- `FAIL`: missing or contradictory to blueprint.

| Blueprint item | Status | Evidence | Required change | Priority |
|---|---|---|---|---|
| Single-phase framing (`Phase 1 - National MVP`) | PASS | `docs/ops/NEXT_BACKLOG.md`, `docs/ops/ALIGNMENT_COVERAGE.md`, `docs/reference_catalog/*` updated from `Phase 2` wording | Keep this language in future docs edits | P0 |
| No DGC governance process | PASS | Repository scan outside blueprint docs returns no `DGC`/`Data Governance Council` references | Maintain CI phrase guard | P1 |
| ITSC methods-only approval | PARTIAL | ITSC approval is now enforced for indicator release submission via `indicator_release_workflow.py` using active + ITSC-marked methodology versions | Add explicit ITSC-only method-approval transition API/UI | P0 |
| Conditional Data Steward review only for flagged-sensitive releases | PASS | `src/nbms_app/services/indicator_release_workflow.py` routes restricted/IPLC releases to steward queue, non-sensitive releases fast-publish | Expand trigger set for licence/embargo flags in a future increment | P0 |
| NBMS not compute engine boundary | PASS | User-facing `recompute` wording replaced with `refresh` semantics in reporting UI/docs; compatibility alias retained | Keep orchestration framing in docs and APIs | P0 |
| FR-001 search/discovery across indicators/targets/datasets | PASS | `GET /api/discovery/search` (`api_spa.py`, `api_urls.py`), Angular discovery panel in `indicator-explorer-page.component.ts`, tests in `test_api_indicator_explorer.py` | Add relevance ranking as future enhancement | P0 |
| FR-002 data/target catalog discovery | PASS | Cross-entity discovery payload returns indicators + targets + datasets with ABAC filtering | Add pagination/sorting controls if needed | P1 |
| FR-003 dashboard summary | PASS | `api_dashboard_summary` plus Angular dashboard; added readiness section by target | Add trend drill-down links if required | P1 |
| FR-004 indicator detail with status metadata + downloads | PASS | `api_indicator_detail` now includes next expected update, maturity, readiness score/status, release workflow; Angular detail page renders these | Add dedicated download action UX on detail page (optional) | P0 |
| FR-005 goal/target pages | PARTIAL | Existing Django target pages + framework mapping flows are operational | Add Angular-first target exploration view | P1 |
| FR-006 reporting tool integration | PASS | NR7/NR8 workspace APIs + PDF/DOCX/JSON export remain operational | Keep contract tests current | P1 |
| FR-007 multi-MEA template packs | PASS | `ReportTemplatePack*` runtime + Ramsar pack + docs updates in `docs/reporting/MEA_TEMPLATE_PACKS.md` | Expand CITES/CMS scaffolds to full packs | P1 |
| FR-008 exports/downloads with access rules | PASS | Existing export gating (approvals + consent) and spatial GeoJSON ABAC controls; verification playbook includes checks | Keep access-matrix tests updated | P1 |
| FR-009/FR-010 source registration + validation + release versioning | PASS | Existing dataset/series/release models and programme ingest workflows remain aligned | None immediate | P1 |
| FR-011 sensitive data handling | PASS | Sensitive indicator release now requires Data Steward approval before publish | Add explicit embargo/licence trigger fields later | P0 |
| FR-012 method submission/versioning for ITSC | PARTIAL | Method versions exist and are now required for release publish eligibility | Add ITSC-specific approval transition workflow and UI controls | P0 |
| FR-013/FR-014 indicator release submission/validation/publish | PASS | New workflow service + endpoint (`/api/indicator-series/{series_uuid}/workflow`), attestation fields + migration, tests in `test_indicator_release_workflow.py` | Add UI submission form for release actions | P0 |
| FR-015 indicator status tracking/readiness | PASS | Added `next_expected_update_on`, `pipeline_maturity`, readiness score/status in API + Angular + dashboard summary | Tune scoring model via policy configuration | P0 |
| FR-016 partner API integration contracts | PASS | Programme runtime contract fields + BIRDIE executable integration remain in place | Extend connectors (Stats SA/SAEON) | P1 |
| FR-017 audit logging | PASS | Audit events captured for release submit/fast-publish/steward approve and existing workflows | Add retention/WORM policy as ops hardening follow-up | P1 |
