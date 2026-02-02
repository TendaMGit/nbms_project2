# HL21.1 Interim Gap Analysis (NBMS proxy)

This document describes the interim HL21.1 “Biodiversity information readiness” metric for the 7NR narrative.

The CBD HL21.1 definition measures the share of GBF headline indicators with national datasets/monitoring schemes that are usable. NBMS does not yet implement the full methodology, so this provides a **coverage + reportability proxy** that is safe under ABAC/consent constraints and deterministic for reporting.

## Interim definitions (two variants)

Variant 1 — **Coverage only**  
Percent of GBF **headline** FrameworkIndicators that have **≥1 mapped national Indicator**.

Variant 2 — **Coverage + reportability proxy**  
Percent of GBF headline FrameworkIndicators that have **≥1 mapped national Indicator** **and** at least one of:
- a linked **IndicatorDataSeries** (visible)
- a linked **DatasetRelease** (visible and approved when an instance is provided)
- national Indicator `reporting_capability` in **yes** or **partial** (added in PR‑B)

Both variants respect ABAC + consent filters; items a user cannot access are excluded from totals.

## Scope semantics

The analysis supports two scopes:

- `selected`: instance‑scoped. Selection follows **alignment coverage kernel** precedence:
  1) Section III/IV progress exists → selected targets/indicators derived from progress  
  2) Else export approvals exist → selected targets/indicators from approvals  
  3) Else **zero selected totals**  
- `all`: all visible registry items for the user (ABAC/consent filtered).

## Command

```
python manage.py hl21_1_gap_analysis --user <email_or_username> --scope all --format json --out-dir out/hl21_1
python manage.py hl21_1_gap_analysis --user <email_or_username> --instance <uuid> --scope selected --format csv --out-dir out/hl21_1
```

Optional:
- `--charts` (requires `matplotlib`)  
- `--no-details` to suppress mapped indicator detail lists

## Outputs

### JSON
`hl21_1_summary.json` includes:
- summary counts for both variants
- by‑target breakdown
- addressed vs not addressed lists

### CSV
- `hl21_1_summary.csv` (single row with both variants)
- `hl21_1_headline_indicators.csv`
- `hl21_1_by_target.csv`

If `--charts` is supplied, PNGs are generated:
- `hl21_1_addressed_pie.png`
- `hl21_1_by_target_bar.png`

## Limitations (vs full HL21.1)
- This does **not** implement the full global methodology (dataset quality, monitoring scheme maturity).
- `reporting_capability` is a **future‑ready** field (PR‑B); if absent it is treated as “unknown”.
- Dataset release linkage is a proxy, not a certification of usability.

## Usage in the 7NR narrative
Use the **coverage + reportability proxy** as a gap analysis:
- “NBMS currently reports X% of GBF headline indicators with any mapped national indicator.”
- “Only Y% have evidence of reportability (series/release/capability), highlighting readiness gaps.”

All statements should include: **“Totals reflect ABAC/consent and may differ by user context.”**
