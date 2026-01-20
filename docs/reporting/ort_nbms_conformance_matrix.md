# ORT to NBMS Conformance Matrix (NR7)

This matrix compares CBD ORT NR7 sections and key blocks to the current NBMS
ReportSectionTemplate and ReportSectionResponse design. It identifies gaps and
the lowest-risk remediation path (seed template changes preferred).

Reference: `docs/reporting/cbd_ort_nr7_template_inventory.md`

## Summary (current)

- NBMS has templates for `section-i`..`section-v` plus `section-other-information` (Annex).
- NBMS section schemas are high-level summaries, while ORT expects more granular
  structures and per-target/per-goal arrays in Sections III and IV.
- ORT indicator data and binary indicator data are separate document types;
  NBMS now provides IndicatorDataSeries/IndicatorDataPoint and BinaryIndicatorQuestion/Response.

## Section I (National context + contacts)

| ORT key | ORT required blocks | NBMS template code | NBMS fields | Gap | Proposed fix |
| --- | --- | --- | --- | --- | --- |
| sectionI | nationalAuthorities, contactPerson, contactDetails, processUndertaken; header.languages, government.identifier | section-i | summary, key_trends, challenges | Missing all ORT Section I fields | Update seed template to include ORT fields (retain existing fields if still needed) |

Notes:
- ORT treats these as structured lstring fields, not a single summary blob.

## Section II (NBSAP + stakeholder engagement)

| ORT key | ORT required blocks | NBMS template code | NBMS fields | Gap | Proposed fix |
| --- | --- | --- | --- | --- | --- |
| sectionII | hasRevisedNbsap, anticipatedNbsapDate, hasStakeholderEngagement, stakeholders, hasNbsapAdopted, hasNbsapAdoptedInfo, anticipatedNbsapAdoptionDate, policyInstrument (+ customValue), implementationProgress | section-ii | policy_measures, financing, capacity_building | Missing all ORT Section II fields | Update seed template to include ORT fields; consider keeping existing fields as optional |

Notes:
- ORT uses multiple typed fields (booleans, enums, dates, term lists, lstrings).
- NBMS currently has only narrative blocks.

## Section III (National targets progress + indicator data)

| ORT key | ORT required blocks | NBMS template code | NBMS fields | Gap | Proposed fix |
| --- | --- | --- | --- | --- | --- |
| sectionIII | array of per-target assessments: target, targetType, mainActionsSummary, levelOfProgress, progressSummary, keyChallengesSummary, actionEffectivenessSummary, sdgRelationSummary; indicatorData blocks (headline/binary/component/complementary/national) | section-iii | progress_overview, indicator_highlights | Structured progress entries now implemented; indicator/binary data available | SectionIIINationalTargetProgress stores per-target narratives and links to IndicatorDataSeries/BinaryIndicatorResponse |

Notes:
- ORT links indicator data documents by identifier from within Section III.
- NBMS currently does not have a per-target response structure for Section III.

## Section IV (Global goals progress + indicator data)

| ORT key | ORT required blocks | NBMS template code | NBMS fields | Gap | Proposed fix |
| --- | --- | --- | --- | --- | --- |
| sectionIV | array of per-goal assessments: gbfGoal, summaryOfProgress; indicatorData blocks (headline/binary/component/complementary/national) | section-iv | support_needs, support_received | Structured progress entries now implemented; indicator/binary data available | SectionIVFrameworkTargetProgress stores per-target narratives and links to IndicatorDataSeries/BinaryIndicatorResponse |

Notes:
- ORT expects multiple goal-level entries, not a single narrative field.

## Section V (Overall assessment)

| ORT key | ORT required blocks | NBMS template code | NBMS fields | Gap | Proposed fix |
| --- | --- | --- | --- | --- | --- |
| sectionV | assessmentSummary | section-v | annex_notes, references | Missing assessmentSummary field | Update seed template to add assessmentSummary (retain annex_notes/references if still needed) |

## Annex / Other Information

| ORT key | ORT required blocks | NBMS template code | NBMS fields | Gap | Proposed fix |
| --- | --- | --- | --- | --- | --- |
| sectionOtherInfo | additionalInformation, additionalDocuments (links/files) | section-other-information | additional_information, additional_documents | Template exists; ORT mapping still needed | Map fields during export; keep fields aligned to ORT expectations |

Notes:
- ORT treats Annex as a separate section with its own key and editor route.

## Indicator data documents (cross-cutting)

| ORT schema | ORT purpose | NBMS current capture | Gap | Proposed fix |
| --- | --- | --- | --- | --- |
| nationalReport7IndicatorData | time-series / dataset data per indicator | IndicatorDataSeries + IndicatorDataPoint | Core data model implemented; export mapping pending | Link Section III/IV progress entries to IndicatorDataSeries |
| nationalReport7BinaryIndicatorData | binary question responses per indicator | BinaryIndicatorQuestion + BinaryIndicatorResponse | Core data model implemented; export mapping pending | Link Section III/IV progress entries to BinaryIndicatorResponse |

## Conformance notes for stable codes

- ORT uses camelCase keys in payloads (sectionI..sectionV, sectionOtherInfo),
  and kebab-case slugs in routes (section-I..section-V, section-other-information).
- NBMS uses kebab-case `section-i`..`section-v`. This is compatible with ORT
  route slugs and can be mapped to payload keys during export.
- A new `section-other-information` template is required for Annex conformance.
