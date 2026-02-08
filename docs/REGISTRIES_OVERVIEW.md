# REGISTRIES OVERVIEW

## Purpose
NBMS registries are programme-driven reference backbones for One Biodiversity operations:
- `Ecosystem` registry for vegetation/ecosystem classes, typology mapping, and risk assessment.
- `Taxon` registry for Darwin Core-first taxon concepts, names, source records, and vouchers.
- `IAS` registry for alien-species baselines and EICAT/SEICAT impact evidence.

These registries are not indicator-specific tables. Programmes produce trusted outputs that indicators consume.

## Data Model Summary

### Ecosystem Registry
- `IucnGetNode`: IUCN Global Ecosystem Typology hierarchy reference.
- `EcosystemType`: VegMap-centric ecosystem unit (realm, biome, bioregion, version).
- `EcosystemTypologyCrosswalk`: explicit mapping from `EcosystemType` to `IucnGetNode` with confidence and review status.
- `EcosystemRiskAssessment`: IUCN RLE-ready criteria A-E + category and review workflow.

### Taxon Registry
- `TaxonConcept`: canonical taxon concept with classification fields and optional GBIF keys.
- `TaxonName`: accepted/synonym/vernacular names with language and preferred flags.
- `TaxonSourceRecord`: source payload, citation, license, and deterministic payload hash.
- `SpecimenVoucher`: DwC-like voucher row with locality sensitivity controls.

### IAS Registry
- `AlienTaxonProfile`: establishment/pathway/degree vocab fields, habitats, and regulatory notes.
- `IASCountryChecklistRecord`: checklist-level import rows (GRIIS or equivalent baseline).
- `EICATAssessment`: EICAT category + mechanisms + confidence + review state.
- `SEICATAssessment`: SEICAT category + wellbeing/activity narrative + confidence + review state.

### Programme Template Catalog
- `ProgrammeTemplate`: reusable programme blueprint for ecosystems/taxa/IAS/protected areas.
- Seeded template codes:
  - `NBMS-PROG-ECOSYSTEMS`
  - `NBMS-PROG-TAXA`
  - `NBMS-PROG-IAS`
  - `NBMS-PROG-PROTECTED-AREAS`

## API Surface
- `GET /api/registries/ecosystems`
- `GET /api/registries/ecosystems/{uuid}`
- `GET /api/registries/taxa`
- `GET /api/registries/taxa/{uuid}`
- `GET /api/registries/ias`
- `GET /api/registries/ias/{uuid}`
- `GET /api/programmes/templates`

## Security and Governance
- ABAC filtering is applied through `filter_queryset_for_user`.
- Sensitive voucher locality is redacted for non-privileged users in `api_registry_taxon_detail`.
- Review workflow fields (`review_status`, reviewer, evidence) are built into crosswalk and assessment entities.
- Provenance fields are retained (`source_system`, `source_ref`, source payload/citation/license).

## Programme Runtime Integration
`run_programme --programme-code <CODE>` now supports registry-linked ingestion paths:
- Ecosystems pipeline triggers VegMap baseline sync.
- Taxa pipeline triggers backbone and voucher sync.
- IAS pipeline triggers GRIIS baseline sync.

Run provenance is stored via monitoring programme run/step/QA/artefact models.

## Demo and Bootstrap Commands
- `python manage.py seed_get_reference`
- `python manage.py sync_vegmap_baseline`
- `python manage.py sync_taxon_backbone --seed-demo`
- `python manage.py sync_specimen_vouchers --seed-demo`
- `python manage.py sync_griis_za --seed-demo`
- `python manage.py seed_programme_templates`
- `python manage.py seed_registry_demo`

## Role Decision (Phase 10)
- Registry view access: any authenticated role (`can_view_registries`).
- Template management access: `SystemAdmin`, `Admin`, `Secretariat`, `Data Steward` (`can_manage_programme_templates`).
- Sensitive locality access: restricted to `SystemAdmin`, `Admin`, `Security Officer`.
- Anonymous users have no registry endpoint access.
