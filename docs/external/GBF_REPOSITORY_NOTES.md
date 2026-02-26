# GBF Indicator Repository Notes

## Sources
- https://www.gbf-indicators.org/metadata/headline/A-1
- https://www.gbf-indicators.org/metadata/headline/B-1
- Local snapshots:
  - `gbf-headline-A-1.html`
  - `gbf-headline-B-1.html`

## Observed Factsheet Structure

The repository headline pages expose structured sections that are useful for NBMS method metadata, including:
- conceptual definition and purpose,
- data sources,
- disaggregation guidance,
- methodological notes and caveats.

## NBMS Design Mapping

Repository metadata is mapped to:
- `IndicatorMethodProfile.summary`
- `IndicatorMethodProfile.required_inputs_json`
- `IndicatorMethodProfile.disaggregation_requirements_json`
- `IndicatorMethodProfile.output_schema_json`
- `IndicatorMethodProfile.readiness_notes`

Implemented model/service files:
- `src/nbms_app/models.py`
- `src/nbms_app/services/indicator_method_sdk.py`
- `src/nbms_app/management/commands/seed_gbf_indicators.py`

## Gap Note

Binary indicator factsheet URL patterns were not consistently resolvable during this run; binary catalog seeding is anchored to COP16/31 Annex I list and can be enriched when stable binary factsheet endpoints are confirmed.
