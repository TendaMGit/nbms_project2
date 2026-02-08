# ADR 0014: Registry Workflow, Gold Marts, and Indicator Integration

- Status: Accepted
- Date: 2026-02-08

## Context
Phase 11 requires registries to be operationally useful for approvals, indicator readiness, and report products.
The system already had registry entities (ecosystem/taxon/IAS), but lacked a consistent transition workflow, evidence gates, and derived summary outputs suitable for dashboards/reports.

## Decision
1. Implement a centralized registry workflow service:
   - `src/nbms_app/services/registry_workflows.py`
   - Supports `submit`, `approve`, `publish`, `reject`
   - Enforces evidence-gated transitions through configurable `ValidationRuleSet` (`REGISTRY_WORKFLOW_DEFAULT`)
   - Writes explicit audit events (`registry_submit`, `registry_approve`, `registry_publish`, `registry_reject`, `registry_link_evidence`)
2. Add generic evidence linking for registry objects:
   - `RegistryEvidenceLink` model keyed by `content_type + object_uuid + evidence`
3. Add registry gold marts:
   - `TaxonGoldSummary`
   - `EcosystemGoldSummary`
   - `IASGoldSummary`
   - Refreshed by `refresh_registry_marts` command and exposed via `/api/registries/gold`
4. Integrate registries into indicator readiness and method execution:
   - `IndicatorRegistryCoverageRequirement` model for per-indicator required registry coverage
   - New method SDK implementations consuming marts:
     - `ecosystem_registry_summary`
     - `ias_registry_pressure_index`
     - `taxon_registry_native_voucher_ratio`
5. Auto-populate report products from registry marts:
   - NBA/GMO/Invasive payloads now include deterministic `auto_sections`, citations, and evidence hooks.

## Consequences
- Positive:
  - Registry approvals are auditable and policy-driven.
  - Indicators can consume standardized registry outputs, not ad-hoc manual data.
  - Report products gain reproducible, machine-generated sections.
- Trade-offs:
  - Gold marts are refreshed by command (or programme), not yet true materialized views with DB-level refresh policies.
  - Registry workflow API is generic and requires UI orchestration for richer reviewer assignment UX.

## Alternatives Considered
- Keep per-model ad-hoc approval logic:
  - Rejected due to drift risk and inconsistent evidence enforcement.
- Build report auto-sections directly from raw registry tables each request:
  - Rejected due to cost and non-deterministic query complexity; marts provide stable summarized outputs.
