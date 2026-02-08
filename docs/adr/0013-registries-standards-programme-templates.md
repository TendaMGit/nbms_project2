# ADR 0013: Reference Registries Standards and Programme Template Runtime

- Status: Accepted
- Date: 2026-02-08
- Owners: NBMS architecture and platform engineering

## Context
NBMS needs a standards-aligned reference backbone for ecosystem, taxon, and IAS information that can be reused across:
- indicator pipelines,
- programme operations,
- report products (NR7, Ramsar, NBA/GMO/Invasive),
- multi-MEA interoperability.

Previous iterations had reporting and indicator scaffolds but lacked full registry entities and programme-template abstraction for registry-driven operations.

## Decision
1. Introduce first-class registries in core data model:
- Ecosystem: `EcosystemType`, `EcosystemTypologyCrosswalk`, `EcosystemRiskAssessment`, `IucnGetNode`.
- Taxon: `TaxonConcept`, `TaxonName`, `TaxonSourceRecord`, `SpecimenVoucher`.
- IAS: `AlienTaxonProfile`, `IASCountryChecklistRecord`, `EICATAssessment`, `SEICATAssessment`.

2. Use standards-first vocab and semantics:
- Darwin Core-compatible establishment/pathway vocab fields.
- GBIF species match enrichment for taxon source records.
- VegMap-centric ecosystem baseline with explicit GET crosswalk review state.
- RLE-ready criteria/category structure for ecosystem risk records.
- EICAT/SEICAT categories and review metadata for IAS impact evidence.

3. Add programme-template runtime:
- New `ProgrammeTemplate` model and seeding commands.
- Template catalog exposed via `/api/programmes/templates`.
- Existing programme runner (`run_programme`) extended to execute registry-specific ingest flows.

4. Preserve governance and safety defaults:
- ABAC filtering remains mandatory on all registry APIs.
- Sensitive specimen localities are redacted unless user has elevated roles.
- Provenance fields are mandatory for imported/source-derived records.

## Consequences
Positive:
- NBMS can run registry-driven workflows instead of indicator-by-indicator custom structures.
- Clear path to ingest national baselines and feed multiple indicator/report outputs.
- Improved standards traceability for audits and partner interoperability.

Tradeoffs:
- Added schema and command surface increases operational complexity.
- External connector quality (source availability, match precision) needs ongoing QA and monitoring.

## Implementation Notes
- Migration: `0038_alientaxonprofile_ecosystemtype_iucngetnode_and_more.py`
- Commands:
  - `seed_get_reference`
  - `sync_vegmap_baseline`
  - `sync_taxon_backbone`
  - `sync_specimen_vouchers`
  - `sync_griis_za`
  - `seed_programme_templates`
  - `seed_registry_demo`
- APIs:
  - `/api/registries/ecosystems*`
  - `/api/registries/taxa*`
  - `/api/registries/ias*`
  - `/api/programmes/templates`

## Follow-up
- Add write APIs/forms for curator workflows (crosswalk and assessment editing).
- Add periodic standards conformance checks against upstream vocab updates.
- Expand programme-template UI wizard and approval transitions.
