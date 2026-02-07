# External Reference Pack (One Biodiversity Hardening V1)

This folder stores external reference material consulted for GBF/MEA alignment and integration design.

## Files

- `cop-16-dec-31-en.pdf`
  - Source: https://www.cbd.int/doc/decisions/cop-16/cop-16-dec-31-en.pdf
  - Purpose: canonical COP16 decision for GBF monitoring framework indicator lists.
- `COP16_31_NOTES.md`
  - Extracted implementation notes from Annex I/II/III used in `seed_gbf_indicators`.

- `gbf-headline-A-1.html`
- `gbf-headline-B-1.html`
  - Source: https://www.gbf-indicators.org/metadata/headline/A-1 and `/B-1`
  - Purpose: factsheet structure and metadata fields (method, disaggregation, data source framing).
- `GBF_REPOSITORY_NOTES.md`
  - Notes on how factsheet metadata was mapped into NBMS method profile fields.

- `birdie_application.json`
- `birdie-swagger-ui.html`
- `BIRDIE_README.md`
  - Sources:
    - https://birdieapp.sanbi.org.za/birdie/swagger-ui/
    - https://birdieapp.sanbi.org.za/birdie/swagger-ui/birdie_application.json
    - https://github.com/AfricaBirdData/BIRDIE
  - Purpose: external pipeline integration contract and endpoint inventory.
- `BIRDIE_NOTES.md`
  - NBMS integration mapping notes and endpoint groups used for connector scaffolding.

- `informea_dart.html`
- `unep_wcmc_dart_tool_news.html`
- `unep_wcmc_dart_cbd_approval_news.html`
  - Purpose: DaRT interoperability context capture.
  - Note: these pages currently resolve to site-level 404 content in this environment; links retained for traceability.
- `DART_NOTES.md`
  - NBMS design notes for DaRT-style "enter once, reuse many times" interoperability.

- `RAMSAR_COP14_NOTES.md`
  - Ramsar COP14 reporting structure notes (Section I-IV framing and implementation indicator questions).
  - Includes source links and access notes where file URLs currently return 404 from this environment.

## Usage

- External requirements are translated into actionable schema/API/workflow changes in:
  - `src/nbms_app/management/commands/seed_gbf_indicators.py`
  - `src/nbms_app/services/indicator_method_sdk.py`
  - `src/nbms_app/models.py` (`IndicatorMethodProfile`, `IndicatorMethodRun`)
- Integration notes are reflected in:
  - `docs/INTEGRATIONS_MATRIX.md`
  - `docs/API_SURFACE_SUMMARY.md`

## Current implementation linkage (this increment)

- GBF full catalog seeding and method readiness:
  - `python manage.py seed_gbf_indicators`
- Ramsar COP14-oriented pack runtime and validation:
  - `src/nbms_app/management/commands/seed_mea_template_packs.py`
  - `src/nbms_app/services/template_packs.py`
- BIRDIE connector and ingestion:
  - `src/nbms_app/integrations/birdie/`
  - `python manage.py seed_birdie_integration`
