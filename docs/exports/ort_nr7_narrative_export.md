# ORT NR7 Narrative Export (v1)

This export provides a minimal, narrative-only NR7 payload based on
ReportSectionTemplate/ReportSectionResponse content.

## Endpoint

- `GET /exports/instances/<uuid>/ort-nr7-narrative.json` (staff-only)

## Output (v1)

The payload includes:
- `schema`: `nbms.ort.nr7.narrative.v1`
- `exporter_version`: `0.1.0`
- `generated_at`: ISO timestamp
- `reporting_instance`: instance + cycle metadata
- `sections`: array of Section I–V + Annex content
- `nbms_meta`: ruleset code, export gating settings, missing required sections

Section content is the raw `response_json` stored in `ReportSectionResponse`.

## Governance (hard blockers)

Export fails if:
- Required sections are missing (per ValidationRuleSet when EXPORT_REQUIRE_SECTIONS=1).
- Missing IPLC consent for any approved IPLC-sensitive items.
- Missing instance approvals for published items (strict gating).

ABAC filtering is enforced by limiting export scope to the current reporting
instance; no cross-org domain data is exported in v1 narrative payloads.

## Explicit exclusions (v1)

Not included:
- Structured Section III/IV per-target/per-goal arrays
- `nationalReport7IndicatorData` documents
- `nationalReport7BinaryIndicatorData` documents
- National/global target alignment maps

These will be addressed in follow-on PRs.
