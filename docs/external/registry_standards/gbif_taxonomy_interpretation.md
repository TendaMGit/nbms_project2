# GBIF Taxonomy Interpretation

- URL:
  - https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation
- Accessed: 2026-02-08

## NBMS mapping
- `sync_taxon_backbone` uses GBIF species match as enrichment, not as immutable truth.
- Match payload is stored in `TaxonSourceRecord.payload_json` with deterministic hash and citation/license fields.
- `TaxonConcept` keeps both local code (`taxon_code`) and GBIF keys (`gbif_taxon_key`, `gbif_usage_key`, `gbif_accepted_taxon_key`) for traceable cross-system joins.
