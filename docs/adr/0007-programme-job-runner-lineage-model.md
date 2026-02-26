# ADR 0007: Monitoring Programme Job Runner and Lineage Model

- Date: 2026-02-06
- Status: Accepted
- Related phase: One Biodiversity Hardening V1 - Phase 3

## Context
NBMS monitoring programmes needed to move from static catalog records to operational objects that can run ingest/validate/compute/publish workflows with governance visibility. Requirements included:
- steward/operator accountability,
- run history and auditability,
- explicit data-quality checks and alerts,
- reproducible lineage summaries,
- Docker-first operation without introducing fragile infrastructure dependencies.

## Decision
Implement a database-backed programme operations runtime with:

1. Extended `MonitoringProgramme` operational metadata:
- `refresh_cadence`, `scheduler_enabled`, `next_run_at`, `last_run_at`
- `pipeline_definition_json`, `data_quality_rules_json`, `lineage_notes`
- `operating_institutions` and steward assignments (`MonitoringProgrammeSteward`)

2. Execution records and lineage:
- `MonitoringProgrammeRun` (queue/running/succeeded/blocked/failed lifecycle)
- `MonitoringProgrammeRunStep` (deterministic ordered step trace)
- `MonitoringProgrammeAlert` (open/ack/resolved QA alerts)

3. Runner model:
- A lightweight queue/runner service in `src/nbms_app/services/programme_ops.py`
- `run_monitoring_programmes` management command for scheduled processing
- API-triggered run-now and dry-run execution from Angular Programme Ops UI

4. Governance controls:
- ABAC object scoping enforced through `filter_monitoring_programmes_for_user`
- steward assignments included in visibility/edit checks
- explicit audit events for queue/start/complete/fail transitions

## Rationale
- Keeps operational state in the same governance domain as reporting/indicator workflows.
- Works reliably in current Docker profiles and Windows host mode.
- Avoids introducing a mandatory Celery worker topology before connector workloads require it.
- Provides immediate lineage and alerting surfaces for operators and reviewers.

## Consequences
- Scheduler execution is currently command-driven (`run_monitoring_programmes`) and can be container-cron or CI triggered.
- JSON pipeline definitions are flexible but require contract hardening as connector count grows.
- Model and API design remains compatible with adding Celery workers later without schema breakage.

## Follow-up
- Add optional Celery worker profile for high-frequency integrations (BIRDIE and future connectors).
- Add metrics for run duration by programme and step type.
- Add alert acknowledgment/resolution actions in API and UI.
