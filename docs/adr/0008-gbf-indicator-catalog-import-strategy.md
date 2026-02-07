# ADR 0008: GBF Indicator Catalog Import Strategy
Date: 2026-02-07
Status: Accepted

## Context
NBMS must scale from a small seed set to full GBF monitoring coverage, including COP16/31 headline and binary indicators, while preserving deterministic behavior and governance controls.

## Decision
- Implement a dedicated command: `python manage.py seed_gbf_indicators`.
- Seed the full COP16/31 GBF catalog baseline:
  - 13 headline indicators.
  - 22 binary indicators.
- Persist indicator method execution metadata using:
  - `IndicatorMethodProfile`
  - `IndicatorMethodRun`
- Standardize method types:
  - `MANUAL`
  - `CSV_IMPORT`
  - `API_CONNECTOR`
  - `SCRIPTED_PYTHON`
  - `SCRIPTED_R_CONTAINER`
  - `SPATIAL_OVERLAY`
  - `SEEA_ACCOUNTING`
  - `BINARY_QUESTIONNAIRE`
- Add a method SDK (`indicator_method_sdk.py`) with input hashing, cache support, and audit events.

## Consequences
- Pros:
  - Full GBF catalog can be seeded repeatably in one command.
  - Indicator readiness is visible in APIs and Angular explorer.
  - Method execution is auditable and deterministic.
- Tradeoffs:
  - Factsheet enrichment is partial until all external metadata endpoints are stable.
  - Long-running method execution is still synchronous; worker offloading remains a follow-up.

## Implementation references
- `src/nbms_app/management/commands/seed_gbf_indicators.py`
- `src/nbms_app/models.py`
- `src/nbms_app/services/indicator_method_sdk.py`
- `src/nbms_app/indicator_methods/`
