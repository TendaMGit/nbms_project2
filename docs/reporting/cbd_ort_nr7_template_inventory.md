# CBD ORT NR7 Template Inventory (Reference)

Source: `..\online-reporting-tool` (read-only)

This inventory summarizes the NR7-related document types, section keys, and
question blocks in the CBD ORT reference implementation. It is a structured
summary (no large verbatim extracts).

## Document types and schema IDs

From `utils/constants.ts`:
- `nationalReport7`
- `nationalTarget7`
- `nationalTarget7Mapping`
- `nationalReport7IndicatorData`
- `nationalReport7BinaryIndicatorData`

These are the canonical schema identifiers used across NR7 routes and storage.

## NR7 report sections (Section I–V + Annex/Other Information)

The NR7 editor uses a `nationalReport7` document body with the following keys
(`stores/nationalReport7.ts` and `components/pages/nr7/my-country/edit/*`):

- `sectionI` (object)
- `sectionII` (object)
- `sectionIII` (array; per-target assessments)
- `sectionIV` (array; per-goal assessments)
- `sectionV` (object)
- `sectionOtherInfo` (object; “Other information”, effectively the Annex)

The route keys for editing sections are:
- `section-I`, `section-II`, `section-III`, `section-IV`, `section-V`
- `section-other-information`

### Section I (national context + contacts)
From `components/pages/nr7/my-country/edit/nr7-edit-section-I.vue`:
- `nationalAuthorities` (lstring, rich)
-, `contactPerson` (lstring)
-, `contactDetails` (lstring)
-, `processUndertaken` (lstring, rich)

Also captured at document level:
- `header.languages` (list)
- `government.identifier` (term)

### Section II (NBSAP + stakeholder engagement)
From `components/pages/nr7/my-country/edit/nr7-edit-section-II.vue`:
- `hasRevisedNbsap` (enum: yes/no/inProgress)
- `anticipatedNbsapDate` (date; when no/inProgress)
- `hasStakeholderEngagement` (boolean)
- `stakeholders` (term list; incl. OTHER + customValue)
- `hasNbsapAdopted` (enum: yes/no/inProgress/other)
- `hasNbsapAdoptedInfo` (lstring)
- `anticipatedNbsapAdoptionDate` (date; when no/other)
- `policyInstrument` (term; may include `customValue`)
- `implementationProgress` (lstring, rich)

### Section III (national target progress + indicator data)
From `components/pages/nr7/my-country/edit/nr7-edit-section-III.vue`:
- `sectionIII[]` is an array of “assessment” objects keyed by target.
- Each assessment includes:
  - `target` (term with `identifier`)
  - `targetType` (e.g., national vs global)
  - `mainActionsSummary` (lstring, rich)
  - `levelOfProgress` (term; progress assessment list)
  - `progressSummary` (lstring, rich)
  - `keyChallengesSummary` (lstring, rich)
  - `actionEffectivenessSummary` (lstring, rich)
  - `sdgRelationSummary` (lstring, rich; optional)
  - `indicatorData` (structured links to indicator-data documents)

Indicator data blocks in Section III reference:
- headline indicators
- binary indicators
- component indicators
- complementary indicators
- other national indicators

### Section IV (global goals progress + indicator data)
From `components/pages/nr7/my-country/edit/nr7-edit-section-IV.vue`:
- `sectionIV[]` is an array of “assessment” objects keyed by global goal.
- Each assessment includes:
  - `gbfGoal` (term with `identifier`)
  - `summaryOfProgress` (lstring, rich)
  - `indicatorData` (structured links to indicator-data documents)

Indicator data blocks include:
- headline indicators
- binary indicators
- component indicators
- complementary indicators
- (plus optional national indicators where mapped)

### Section V (overall assessment)
From `components/pages/nr7/my-country/edit/nr7-edit-section-V.vue`:
- `sectionV.assessmentSummary` (lstring, rich)

### Section Other Information (Annex)
From `components/pages/nr7/my-country/edit/nr7-edit-section-other-information.vue`:
- `sectionOtherInfo.additionalDocuments` (list of links/files)
- `sectionOtherInfo.additionalInformation` (lstring, rich)

## Indicator data documents

NR7 indicator data is stored as separate documents:

- `nationalReport7IndicatorData`
- `nationalReport7BinaryIndicatorData`

Editor components:
- `nr7-add-indicator-data.vue` (time-series / dataset-style data)
- `nr7-add-binary-indicator-data.vue` (binary question responses)

Common fields (both indicator data document types):
- `header.schema`, `header.languages`
- `government.identifier`
- `indicator` (identifier / reference to indicator term)

### Non-binary indicator data (nationalReport7IndicatorData)
Key fields (summary from `nr7-add-indicator-data.vue`):
- `sourceOfData` (enum: national / availableDataset / noData / notRelevant)
- `sourceOfDataInfo` (lstring; when noData/notRelevant)
- `data` (national dataset upload or data table)
- global data fields when using available datasets
- `comments` (lstring, rich)

### Binary indicator data (nationalReport7BinaryIndicatorData)
Key fields (summary from `nr7-add-binary-indicator-data.vue`):
- responses stored under a per-question-set key (see below)
- `comments` (lstring, rich)

## Binary indicator question sets

From `app-data/binary-indicator-questions.ts`:

- Data is a list of question groups.
- Each group includes:
  - `key` (e.g., `binaryResponseGoalB`, `binaryResponseTarget1`)
  - `target` (e.g., `GBF-GOAL-B`)
  - `binaryIndicator` (e.g., `KMGBF-INDICATOR-BIN-B`)
  - `questions[]` (question objects)
- Each question includes:
  - `key`, `section`, `number`
  - `type` (typically `option`)
  - `title`
  - `multiple` (boolean)
  - `options[]` (common values: no / underDevelopment / partially / fully)
  - `mandatory` (boolean)

Binary question keys span GBF goal/target identifiers (e.g., Goal B/C and
Targets 1, 5, 6, 8, 9, 12, 13, 14, 15, 16, 17, 20, 22, 23).

## National target document structure (for alignment context)

From `types/schemas/ENationalTarget7.ts`:
- `globalGoalAlignment` (term list)
- `globalTargetAlignment` (term list with degreeOfAlignment)
- `implementingConsiderations` + `implementingConsiderationsInfo`
- Indicator lists:
  - `headlineIndicators`
  - `binaryIndicators`
  - `componentIndicators`
  - `complementaryIndicators`
  - `otherNationalIndicators` (identifier + lstring value)

From `types/schemas/ENationalTarget7Mapping.ts`:
- `globalGoalOrTarget` (term)
- `referencePeriod[]` per headline indicator
- `elementOfGlobalTargetsInfo` (lstring)

## Notes / implications for NBMS mapping

- ORT uses stable section keys in camelCase (sectionI..V, sectionOtherInfo),
  while edit routes use kebab-case section slugs.
- Section III and IV are array-based and expect per-target/per-goal objects
  with indicator data references.
- Indicator data and binary indicator data are separate document types and can
  be linked by identifier from Section III/IV.
