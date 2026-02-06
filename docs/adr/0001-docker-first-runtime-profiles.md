# ADR 0001: Docker-First Runtime Profiles

- Status: Accepted
- Date: 2026-02-06

## Context
NBMS needs reproducible deployment for national reporting workflows. Local Windows development must still work without Docker, but delivery and CI need deterministic infrastructure.

## Decision
- Keep Docker as the default reproducible infrastructure path.
- Maintain two runtime profiles:
  - `minimal`: core services needed for workflow execution (PostGIS, Redis, MinIO, backend runtime path).
  - `spatial`: `minimal` plus GeoServer and spatial integrations.
- Keep Windows no-Docker mode as a supported fallback for contributors and constrained environments.

## Consequences
- Reduces "works only on my machine" drift for integration testing.
- Requires profile-specific docs and smoke checks.
- Backend/frontend containerization can progress incrementally without blocking existing host-run workflows.
