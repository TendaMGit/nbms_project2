# ADR 0009: BIRDIE Integration Connector Pattern
Date: 2026-02-07
Status: Accepted

## Context
NBMS needs to integrate external biodiversity pipelines without duplicating upstream analytics. BIRDIE is the first connector and must establish a reusable pattern.

## Decision
- Implement an explicit integration module:
  - `src/nbms_app/integrations/birdie/client.py`
  - `src/nbms_app/integrations/birdie/service.py`
- Use connector-first ingestion:
  - Pull API payloads when configured.
  - Fall back to deterministic fixture data for reproducible local/dev operation.
- Persist lineage by data layer using `IntegrationDataAsset`:
  - `bronze` raw snapshots
  - `silver` normalized entities
  - `gold` indicator-ready records
- Add BIRDIE domain models:
  - `BirdieSpecies`
  - `BirdieSite`
  - `BirdieModelOutput`
- Register a BIRDIE method implementation (`birdie_api_connector`) in indicator method registry.
- Expose BIRDIE dashboard API and management command:
  - `GET /api/integrations/birdie/dashboard`
  - `python manage.py seed_birdie_integration`

## Consequences
- Pros:
  - Integration can run immediately with or without live endpoint access.
  - Bronze/silver/gold lineage is auditable in-database.
  - Pattern generalizes to additional connectors.
- Tradeoffs:
  - Statistical model execution remains upstream (API/fixture sourced) for now.
  - High-volume ingestion may require async worker scaling in future.

## Implementation references
- `src/nbms_app/models.py`
- `src/nbms_app/integrations/birdie/`
- `src/nbms_app/services/programme_ops.py`
- `src/nbms_app/api_spa.py`
