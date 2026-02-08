# ADR 0012: Spatial Baselines Programme + Overlay Indicator Method

- Status: Accepted
- Date: 2026-02-08

## Context

NBMS Phase 8 requires spatial operations to be programme-driven and indicator-ready, not ad hoc:

- real open-licensed boundary/protected-area sources must sync reliably in Docker,
- a monitoring programme run must orchestrate ingest/validate/publish with lineage and QA,
- indicator computation must consume spatial outputs with provenance and deterministic results.

## Decision

1. Spatial ingest is executed through the `NBMS-SPATIAL-BASELINES` monitoring programme pipeline.
   - Command entrypoint: `python manage.py run_programme --programme-code NBMS-SPATIAL-BASELINES`
   - Steps: source sync, QA validation, optional GeoServer publish, overlay compute.

2. Source sync degrades safely when upstream refresh is temporarily unavailable.
   - If a source fetch fails but a prior snapshot exists, sync status is `skipped` and existing data remains authoritative.
   - This preserves reproducibility and prevents hard pipeline failure on transient network/provider issues.

3. A real `SPATIAL_OVERLAY` method is first-class in the indicator method runtime.
   - Protected area layer + admin boundary layer produce province-disaggregated coverage outputs.
   - Outputs are written to `IndicatorDataSeries`/`IndicatorDataPoint` with `programme_run` and dataset-release provenance.

4. UI exposure aligns to this operational contract.
   - Programme Ops surfaces run status, QA, and artefacts.
   - Indicator detail surfaces trend + province disaggregation + map outputs with last-refresh/run metadata.

## Consequences

- Spatial operations are auditable and repeatable from one command in Docker.
- Indicator readiness now depends on explicit operational pipeline state, not manual data pushes.
- Upstream source outages no longer collapse the entire programme run when valid baseline data already exists.
- Additional overlay indicators can reuse the same method/profile + programme-run provenance pattern.
