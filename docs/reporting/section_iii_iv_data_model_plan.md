# Section III/IV data model plan (Phase 4B)

This document outlines the next step for structured Section III/IV storage,
building on the Phase 4A indicator and binary indicator data layer.

## Scope and principles

- No legacy schema ports.
- Reuse IndicatorDataSeries/IndicatorDataPoint for tabular indicator data.
- Reuse BinaryIndicatorQuestion/BinaryIndicatorResponse for binary questions.
- Link progress entries to targets/goals and indicator data rather than
  duplicating indicator values in Section III/IV.

## Planned Phase 4B models (proposed)

1) TargetProgressEntry
- reporting_instance (FK)
- national_target (FK)
- progress_status (enum)
- summary_narrative (text)
- actions_taken (text)
- outcomes (text)
- challenges (text)
- support_needs (text)
- references (JSON list of evidence ids/urls)
- indicator_series (M2M -> IndicatorDataSeries)
- binary_responses (M2M -> BinaryIndicatorResponse)

2) GoalProgressEntry
- reporting_instance (FK)
- framework_target or framework_goal (FK, if modeled)
- summary_narrative (text)
- indicator_series (M2M -> IndicatorDataSeries)
- binary_responses (M2M -> BinaryIndicatorResponse)

## Linking strategy

- Section III: one TargetProgressEntry per NationalTarget.
- Section IV: summary entries aligned to FrameworkTarget/Goal (GBF).
- IndicatorDataSeries is stored once per indicator and referenced by entries.
- BinaryIndicatorResponse is per instance and referenced by entries.

## Readiness and governance (Phase 4B)

- Readiness checks should ensure a progress entry exists for each required
  target/goal and that required narratives are filled.
- ABAC and consent rules remain enforced via the linked indicator/binary data.
- Instance export approval gates remain authoritative.
