# ORT 7NR Mapping Spec (NBMS Project 2)

This document defines the v1 mapping between NBMS Project 2 data and the CBD ORT 7NR
export shape. It is a mapping spec only (no schema changes), and it is scoped to
what NBMS Project 2 currently captures.

## Scope (v1)

Included:
- ReportingInstance metadata (cycle, version, status, freeze info)
- Section responses from ReportSectionTemplate/ReportSectionResponse
- Approved + published NationalTarget, Indicator, Evidence, Dataset, DatasetRelease
- ABAC filtering, instance-scoped approvals, and consent gating
- ValidationRuleSet-driven required section enforcement
- Deterministic ordering and stable identifiers
- exporter_version and nbms_meta block

Deferred (explicit TODOs in mapping tables):
- Global goals/targets alignment (ORT nationalTarget7 fields)
- Binary indicator question responses (ORT nationalReport7BinaryIndicatorData)
- Indicator time series data (ORT nationalReport7IndicatorData)
- Formal government identifier (country code)
- Evidence-to-ORT links beyond basic URL mapping

## Non-negotiable gates (authoritative)

Export must fail if any of the following fail:
1) Required sections missing or incomplete per ValidationRuleSet
   - Use the active ruleset from ValidationRuleSet (instance or cycle override first)
   - If EXPORT_REQUIRE_SECTIONS is true, missing required sections block export
2) Instance-scoped approvals missing
   - Only include objects with InstanceExportApproval decision=APPROVED
3) IPLC/CARE consent missing
   - ConsentRecord for IPLC-sensitive items must be GRANTED for the instance or globally
4) ABAC filtering
   - If a user cannot see an object, it must not be exported

Canonical functions (NBMS Project 2) to reuse:
- readiness: get_instance_readiness (section completeness + consent blockers)
- approvals: approved_queryset
- consent: consent_is_granted / requires_consent
- ABAC: filter_queryset_for_user

## Output package shape (v1)

The exporter emits a single JSON object:

```
{
  "exporter_version": "0.1",
  "generated_at": "2026-01-16T12:34:56Z",
  "documents": {
    "nationalReport7": [ ... ],
    "nationalTarget7": [ ... ],
    "nationalTarget7Mapping": [],
    "nationalReport7IndicatorData": [],
    "nationalReport7BinaryIndicatorData": []
  },
  "nbms_meta": {
    "reporting_instance_uuid": "...",
    "reporting_cycle_code": "...",
    "reporting_cycle_title": "...",
    "reporting_instance_status": "...",
    "ruleset_code": "...",
    "export_require_sections": true,
    "missing_required_sections": []
  }
}
```

Notes:
- The package layout mirrors ORT document types, but v1 only populates the pieces
  NBMS currently supports. Empty arrays are intentional where NBMS has no data model.

## Mapping conventions

LString:
- ORT ELstring values are dictionaries of locale -> string.
- NBMS has no locale model for sections. Use settings.LANGUAGE_CODE (default "en")
  and map a plain string to {"en": "<value>"}.
- If a response value is already a dict with locale-like keys, pass it through.

Term:
- ORT ETerm supports { identifier, title }.
- NBMS can populate identifier with a stable code/uuid; title is optional.

Link:
- ORT ELink supports { url, name, tags, language }.
- NBMS can map evidence source_url (or file URL) to url and title to name.

Determinism:
- Sort lists by stable keys (code, title, ordering, created_at where applicable)
- Use stable identifiers (object UUIDs) rather than random UUIDs

Redaction:
- If a required sensitive item lacks consent, block export (do not redact)
- If an optional sensitive item lacks consent, omit it (no placeholders)
- Do not emit data for objects not visible under ABAC

## Field mapping tables

### 1) Root package

| ORT/Export Path | Type | NBMS source | Notes |
| --- | --- | --- | --- |
| exporter_version | string | Constant "0.1" | Bump when output changes. |
| generated_at | string (ISO 8601) | timezone.now() | UTC ISO string. |
| documents | object | See below | ORT document arrays. |
| nbms_meta.reporting_instance_uuid | string | ReportingInstance.uuid | Stable UUID. |
| nbms_meta.reporting_cycle_code | string | ReportingCycle.code | |
| nbms_meta.reporting_cycle_title | string | ReportingCycle.title | |
| nbms_meta.reporting_instance_status | string | ReportingInstance.status | |
| nbms_meta.ruleset_code | string | ValidationRuleSet.code | Active ruleset used. |
| nbms_meta.export_require_sections | bool | settings.EXPORT_REQUIRE_SECTIONS | |
| nbms_meta.missing_required_sections | list[string] | readiness details | From get_instance_readiness. |

### 2) Document header (applies to all ORT docs)

| ORT Path | Type | NBMS source | Notes |
| --- | --- | --- | --- |
| header.schema | string | Constant per document | Example: "nationalReport7". |
| header.identifier | string (UUID) | Object uuid or derived | Use object.uuid where possible. |
| header.languages | list[string] | settings.LANGUAGE_CODE | Default ["en"]. |
| header.legacyIdentifier | string | "" | TODO: optional legacy mapping. |
| government.identifier | string | settings.NBMS_ORT_GOVERNMENT_ID | TODO: add official code. |

### 3) nationalReport7

V1 uses ReportingInstance + section responses. NBMS does not natively store ORT
section fields (Section I-V) at the same granularity; we export raw response_json
for each section and only map ORT fields when they exist by key.

| ORT Path | Type | NBMS source | Notes |
| --- | --- | --- | --- |
| documents.nationalReport7[*].header | object | See header mapping | |
| documents.nationalReport7[*].government | term | See header mapping | |
| documents.nationalReport7[*].sectionI | object | ReportSectionResponse.response_json for code "section-i" | Field-level keys are best-effort. |
| documents.nationalReport7[*].sectionII | object | response_json for "section-ii" | |
| documents.nationalReport7[*].sectionIII | object | response_json for "section-iii" | ORT expects per-target array; NBMS exports raw section narrative. |
| documents.nationalReport7[*].sectionIV | object | response_json for "section-iv" | ORT expects per-goal array; NBMS exports raw section narrative. |
| documents.nationalReport7[*].sectionV | object | response_json for "section-v" | |
| documents.nationalReport7[*].sectionOtherInfo.additionalInformation | lstring | response_json["additional_information"] if present | TODO: template alignment. |
| documents.nationalReport7[*].sectionOtherInfo.additionalDocuments | list[link] | Evidence.source_url / file.url | Optional; only if safely linkable. |
| documents.nationalReport7[*].additionalInformation | lstring | response_json fallback | Optional; use if sectionOtherInfo not present. |
| documents.nationalReport7[*].additionalDocuments | list[link] | Evidence items | Optional. |
| documents.nationalReport7[*].notes | string | ReportingInstance.notes | |

Recommended ORT key alignment for section responses (future template updates):
- Section I: nationalAuthorities, contactPerson, contactDetails, processUndertaken
- Section II: hasRevisedNbsap, anticipatedNbsapDate, hasStakeholderEngagement,
  stakeholders, hasNbsapAdopted, hasNbsapAdoptedInfo, anticipatedNbsapAdoptionDate,
  policyInstrument, implementationProgress
- Section III: mainActionsSummary, levelOfProgress, progressSummary,
  keyChallengesSummary, actionEffectivenessSummary, sdgRelationSummary
- Section IV: summaryOfProgress
- Section V: assessmentSummary

### 4) nationalTarget7

| ORT Path | Type | NBMS source | Notes |
| --- | --- | --- | --- |
| documents.nationalTarget7[*].header | object | See header mapping | header.identifier = NationalTarget.uuid |
| documents.nationalTarget7[*].government | term | See header mapping | |
| documents.nationalTarget7[*].title | lstring | NationalTarget.title | |
| documents.nationalTarget7[*].description | lstring | NationalTarget.description | |
| documents.nationalTarget7[*].sequence | number | Order by NationalTarget.code | Use 1..N after sort. |
| documents.nationalTarget7[*].globalGoalAlignment | list[term] | TODO | NBMS has no global goals model. |
| documents.nationalTarget7[*].globalTargetAlignment | list[term] | TODO | NBMS has no global target alignment. |
| documents.nationalTarget7[*].degreeOfAlignmentInfo | lstring | TODO | |
| documents.nationalTarget7[*].implementingConsiderations | list[term] | TODO | |
| documents.nationalTarget7[*].implementingConsiderationsInfo | lstring | TODO | |
| documents.nationalTarget7[*].mainPolicyOfMeasureOrActionInfo | lstring | NationalTarget.description (fallback) | Placeholder only. |
| documents.nationalTarget7[*].headlineIndicators | list[term] | TODO | NBMS has no indicator type classification. |
| documents.nationalTarget7[*].binaryIndicators | list[term] | TODO | |
| documents.nationalTarget7[*].componentIndicators | list[term] | TODO | |
| documents.nationalTarget7[*].complementaryIndicators | list[term] | TODO | |
| documents.nationalTarget7[*].otherNationalIndicators | list[object] | Indicator.code + title | Map approved, published indicators. |
| documents.nationalTarget7[*].hasNonStateActors | bool | TODO | |
| documents.nationalTarget7[*].nonStateActorsInfo | lstring | TODO | |
| documents.nationalTarget7[*].additionalImplementation | term | TODO | |
| documents.nationalTarget7[*].additionalImplementationInfo | lstring | TODO | |
| documents.nationalTarget7[*].additionalInformation | lstring | NationalTarget.review_note | Optional. |
| documents.nationalTarget7[*].additionalDocuments | list[link] | Evidence for target | Optional. |
| documents.nationalTarget7[*].notes | string | NationalTarget.review_note | |

Indicator mapping rules for otherNationalIndicators (v1):
- identifier = Indicator.code or "NBMS-IND-" + Indicator.uuid
- value = lstring(Indicator.title)

### 5) nationalTarget7Mapping (v1 empty)

NBMS does not implement ORT target mapping records. The exporter emits an empty list.

### 6) nationalReport7IndicatorData (v1 empty)

NBMS does not yet store indicator time-series values aligned with ORT schema.
Exporter emits an empty list. Future mapping could use a dedicated indicator
data model or extend DatasetRelease with structured data.

### 7) nationalReport7BinaryIndicatorData (v1 empty)

NBMS does not store binary indicator question responses. Exporter emits an empty
list. Future mapping requires a binary question model keyed to ORT question sets.

## ABAC visibility rules

For each model (NationalTarget, Indicator, Evidence, Dataset, DatasetRelease):
- Base queryset is filtered by filter_queryset_for_user(user)
- Only include status=PUBLISHED
- Only include objects approved for the reporting instance
- If IPLC-sensitive, consent must be granted for the instance (or global)

## Instance-scoped approvals

Use InstanceExportApproval where:
- reporting_instance = current instance
- decision = APPROVED
- approval_scope = "export"

Only approved objects are eligible for export.

## Consent gating

For IPLC-sensitive objects:
- ConsentRecord(status=GRANTED) must exist for the instance, or globally
- If missing, export is blocked (do not redact)

## ValidationRuleSet-driven completeness

Required sections and required fields are derived from ValidationRuleSet:
- applies_to=INSTANCE (instance uuid) overrides
- applies_to=CYCLE (cycle code) overrides
- else code="7NR_DEFAULT"

If required sections are missing and EXPORT_REQUIRE_SECTIONS is true, export is blocked.

## TODOs (tracked for later phases)

1) Introduce a configurable government identifier (ISO country code).
2) Add global goals/targets alignment model or mapping table.
3) Add indicator data model aligned to ORT indicator data schema.
4) Add binary indicator response model aligned to ORT binary question sets.
5) Align ReportSectionTemplate fields to ORT section keys for higher fidelity.
