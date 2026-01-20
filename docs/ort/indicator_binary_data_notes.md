# ORT NR7 indicator + binary data notes

Sources reviewed (local clone of `scbd/online-reporting-tool`):
- `app-data/binary-indicator-questions.ts`
- `i18n/dist/app-data/binary-indicator-questions.json`
- `types/controls/indicator-mapping.ts`
- `app-data/indicators.ts`
- `services/national-report-7-service.ts`

## Indicator data (nationalReport7IndicatorData)

`types/controls/indicator-mapping.ts` defines a minimal indicator data row:
- `indicatorCode` (string)
- `hasDisaggregation` (boolean)
- `disaggregationType` (string)
- `disaggregation` (string)
- `year` (number)
- `unit` (string)
- `value` (number)
- `footnote` (string)

`app-data/indicators.ts` provides indicator mappings:
- `identifier` (e.g., `GBF-INDICATOR-A.1`, `KMGBF-INDICATOR-BIN-B`)
- `code` (short code)
- `title` (indicator title)

`services/national-report-7-service.ts`:
- loads indicator data using schema names `NATIONAL_REPORT_7_INDICATOR_DATA` and
  `NATIONAL_REPORT_7_BINARY_INDICATOR_DATA`
- maps indicator data to targets/goals using indicator identifiers
- does not expose extra fields beyond the mapping structure above

## Binary indicator questions (nationalReport7BinaryIndicatorData)

`app-data/binary-indicator-questions.ts` defines a function
`getBinaryIndicatorQuestions(locale)` returning question groups.

Group-level fields:
- `key` (e.g., `binaryResponseGoalB`, `binaryResponseTarget1`)
- `target` (e.g., `GBF-GOAL-B`, `GBF-TARGET-1`)
- `binaryIndicator` (e.g., `KMGBF-INDICATOR-BIN-1`)
- `title` (often empty in source)
- `questions` (nested list)

Question fields (nested, recursive):
- `key` (stable question id, e.g., `b_1`, `q1`)
- `section` (string, e.g., `goalB`, `target1`)
- `number` (human label, e.g., `B.1`, `1.1`)
- `type` (`option`, `checkbox`, `header`)
- `title` (translation key resolved via `t("...")`)
- `multiple` (boolean; true for checkboxes)
- `options` (list of `{ value, title }`)
- `mandatory` (boolean)
- `questions` (nested sub-questions when `type: header`)
- `validations` (optional; e.g., min selection)

`server/routes/national-report-questions/binary-indicators.ts` can return a
flattened list that merges group fields into each question.

Option values include:
- `yes`, `no`, `underDevelopment`, `partially`, `fully`, `notApplicable`
- `yesForSomeUrbanAreas`, `yesForAllUrbanAreas`, `noParticipatoryProcess`
- multi-select categories (e.g., `forTerrestrialPlanning`, `agriculture`,
  `climateChange`, `oceanAcidification`, `mitigation`, `adaptation`)

Translation strings are stored in
`i18n/dist/app-data/binary-indicator-questions.json` keyed by locale and
translation key.
