# ORT NR7 Export (v2, structured)

This export extends the narrative-only v1 payload by including structured
Section III/IV progress entries and embedding referenced indicator/binary data.

## Endpoint

- `GET /exports/instances/<uuid>/ort-nr7-v2.json` (staff-only)

## Output (v2)

The payload includes:
- `schema`: `nbms.ort.nr7.v2`
- `exporter_version`: `0.2.0`
- `generated_at`: ISO timestamp
- `reporting_instance`: instance + cycle metadata
- `sections`: Section I–V + Annex narrative content
- `section_iii_progress`: per-national-target progress entries
- `section_iv_progress`: per-framework-target progress entries
- `indicator_data_series`: embedded time-series data used by the instance
- `binary_indicator_data`: embedded binary indicator responses used by the instance
- `nbms_meta`: ruleset code, export gating settings, conformance flags

## Governance (hard blockers)

Export fails if:
- Required sections are missing (per ValidationRuleSet when EXPORT_REQUIRE_SECTIONS=1).
- Missing instance approvals for published items.
- Missing IPLC consent for approved IPLC-sensitive items.
- Any progress entry references indicator series, binary responses, evidence, or dataset releases
  that are not export-eligible for the requesting user and instance.

ABAC filtering is enforced for all referenced objects; invisible objects are not exported.

## Determinism

- Section III entries sorted by national target code.
- Section IV entries sorted by framework target code.
- Indicator series sorted by framework indicator code, then national indicator code/uuid.
- Data points sorted by year and stable disaggregation key ordering.

## v1 vs v2

- v1 exports narratives only (`nbms.ort.nr7.narrative.v1`).
- v2 adds structured progress arrays and embeds indicator/binary data used by the instance.
- v1 endpoint remains unchanged for compatibility.

## Known limitations (v2)

- ORT schema key names are still NBMS-flavored and may require a future mapping layer.
- Progress entries are exported as NBMS structures, not yet transformed into ORT’s exact
  per-target/per-goal arrays.
