# Section III/IV data model plan (Phase 4B)

This document describes the structured Section III/IV storage implemented in
Phase 4B, building on the Phase 4A indicator and binary indicator data layer.

## Scope and principles

- No legacy schema ports.
- Reuse IndicatorDataSeries/IndicatorDataPoint for tabular indicator data.
- Reuse BinaryIndicatorQuestion/BinaryIndicatorResponse for binary questions.
- Link progress entries to targets/goals and indicator data rather than
  duplicating indicator values in Section III/IV.

## Implemented Phase 4B models

1) SectionIIINationalTargetProgress
- reporting_instance (FK)
- national_target (FK)
- progress_status (enum)
- summary, actions_taken, outcomes, challenges, support_needed (text)
- period_start, period_end (date)
- indicator_data_series (M2M -> IndicatorDataSeries)
- binary_indicator_responses (M2M -> BinaryIndicatorResponse)
- evidence_items (M2M -> Evidence)
- dataset_releases (M2M -> DatasetRelease)
- unique (reporting_instance, national_target)

2) SectionIVFrameworkTargetProgress
- reporting_instance (FK)
- framework_target (FK)
- progress_status (enum)
- summary, actions_taken, outcomes, challenges, support_needed (text)
- period_start, period_end (date)
- indicator_data_series (M2M -> IndicatorDataSeries)
- binary_indicator_responses (M2M -> BinaryIndicatorResponse)
- evidence_items (M2M -> Evidence)
- dataset_releases (M2M -> DatasetRelease)
- unique (reporting_instance, framework_target)

## Linking strategy

- Section III: one progress entry per NationalTarget per instance.
- Section IV: one progress entry per FrameworkTarget per instance.
- IndicatorDataSeries is stored once per indicator and referenced by entries.
- BinaryIndicatorResponse is per instance and referenced by entries.

## Scope semantics

- In-scope NationalTargets for Section III are the approved targets for the
  reporting instance (InstanceExportApproval), plus any targets implied by
  approved indicators for the instance.
- In-scope FrameworkTargets for Section IV are derived from in-scope
  NationalTargets via NationalTargetFrameworkTargetLink.
- If no targets are approved for the instance, no Section III/IV entries are
  required yet.

## Readiness and governance

- Readiness checks require progress entries for in-scope targets when
  sections III/IV are required by the active ValidationRuleSet.
- ABAC and consent rules remain enforced via the linked indicator/binary data.
- Instance export approval gates remain authoritative.
