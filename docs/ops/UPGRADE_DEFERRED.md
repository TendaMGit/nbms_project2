# Deferred High-Risk Upgrades

Date: 2026-02-27  
Branch: `chore/upgrade-track-redo-2026Q1`

This document records dependency/runtime upgrades intentionally deferred from the controlled refresh PR.

## Deferred Items

1. Python base image `3.12-slim -> 3.14-slim`
- Status: Deferred.
- Why deferred: Runtime major-version jump with elevated risk for binary wheels, C-extension compatibility, and framework/toolchain behavior.
- Required validation before approval:
  - Rebuild backend images on candidate runtime (`3.13` first, then `3.14` only if justified).
  - Run full backend/frontend/e2e gates.
  - Run production compose smoke with database migrations and health checks.
  - Validate third-party binary dependencies (`psycopg2-binary`, geospatial libs, cairo/reporting stack).
- Recommended window: Dedicated platform/runtime upgrade sprint.

2. Redis `5.x -> 7.x`
- Status: Deferred.
- Why deferred: Server major-version upgrade can affect persistence, configuration defaults, and client behavior under load.
- Required validation before approval:
  - Upgrade in isolated branch with representative cache/session workloads.
  - Verify startup configuration and health checks.
  - Run regression tests covering cache-backed flows, auth/session behavior, and rate limiting.
  - Perform rolling restart compatibility test in compose/Kubernetes-equivalent flow.
- Recommended window: Infrastructure compatibility window with rollback rehearsal.

3. `django-guardian 2.4.0 -> 3.3.0`
- Status: Deferred.
- Why deferred: Authorization behavior is security-sensitive; major upgrade may change object-permission semantics and query behavior.
- Required validation before approval:
  - Run full RBAC/ABAC regression suite.
  - Verify object-level permission assignment/revocation flows in API and admin paths.
  - Validate all role-gated UI/API smoke tests.
  - Perform targeted audit-log verification for approval/publish actions.
- Recommended window: Security-focused change window with explicit reviewer sign-off.

## Re-enable Criteria

These deferred upgrades should only be included when:
- A dedicated upgrade branch exists.
- All gates pass (`manage.py check`, `pytest -q`, frontend build/test/e2e, prod compose build/up + smoke).
- Rollback steps are documented and tested.
