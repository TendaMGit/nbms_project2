# ADR 0004: Indicator Workflow V1 Pack and Governance Lifecycle

- Status: Accepted
- Date: 2026-02-06

## Context
NBMS needs a usable end-to-end indicator workflow immediately, but full GBF computation automation is a larger program of work. The system must prove registry-to-publication behavior with governance controls now.

## Decision
- Implement a seeded v1 pack of four GBF/NBA-inspired indicators with complete lifecycle wiring:
  - metadata and framework mapping
  - methodology + methodology version
  - dataset/catalog/release linkage
  - data series + datapoints
  - evidence linkage
  - workflow status transitions and publish gate checks
  - monitoring programme linkage as source-of-data structure
- Keep workflow engine generic using existing `LifecycleStatus` + workflow services.
- Use idempotent management command `seed_indicator_workflow_v1` for reproducible bootstrap.

## Consequences
- Provides immediate demonstration of controlled indicator lifecycle for dashboards, APIs, and exports.
- Keeps migration risk low by extending existing model surfaces instead of introducing new orchestration framework.
- Defers full indicator-specific computation runners and national-scale data ingestion pipelines to subsequent increments.
