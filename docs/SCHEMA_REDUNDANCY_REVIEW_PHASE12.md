# Schema Redundancy Review - Phase 12

Date: 2026-02-09
Branch: `feat/national-report-collab-signoff-v1`

## Scope
- `ReportingInstance`
- `ReportSectionResponse`
- `ReportTemplatePack*`
- structured Section I-V tables
- review/approval/audit tables

## Findings
1. `ReportSectionResponse` vs `ReportTemplatePackResponse`
- `ReportSectionResponse` is legacy narrative storage from early NR flows.
- `ReportTemplatePackResponse` is current runtime MEA pack storage already used by Angular template-pack editing.
- Safe decision: keep both in Phase 12.
Reason: ORT export and legacy templates still reference `ReportSectionResponse`, while Phase 12 collaboration/sign-off is implemented on `ReportTemplatePackResponse`.

2. Structured Section I-V tables vs template-pack JSON responses
- Structured tables (`SectionIReportContext`, `SectionIINBSAPStatus`, `SectionIIINationalTargetProgress`, `SectionIV*`, `SectionVConclusions`) are required by existing ORT export/readiness flows.
- Template-pack responses are required for multi-author editing, suggestions, and section-level revision chains.
- Safe decision: dual-track with synchronization by workflow/export services where needed; no destructive merge in this phase.

3. Existing review tables (`ReviewDecision`, `ReportingSnapshot`) vs new sign-off workflow
- Existing tables support snapshot-based review history.
- New workflow tables support role-explicit sign-off chain and hash-linked approvals.
- Safe decision: keep both.
Reason: they serve distinct audit purposes and migration risk is high if collapsed now.

## Candidate Merges Deferred
1. Merge `ReportSectionResponse` into `ReportTemplatePackResponse`
- Deferred: high migration risk, impacts older templates and tests.

2. Replace `ReviewDecision` with `ReportWorkflowAction`
- Deferred: existing UI/tests rely on `ReviewDecision`.

3. Collapse section-specific structured tables into generic JSON-only storage
- Deferred: would regress strong typed validation and ORT compatibility.

## Phase 12 Data Strategy
- Canonical collaborative authoring state: `ReportTemplatePackResponse` + revisions/comments/suggestions.
- Canonical sign-off chain: `ReportWorkflow*`.
- Canonical export artifacts and evidence package: `ReportExportArtifact` + `ReportDossierArtifact`.
- Existing structured section tables remain authoritative for compatibility-sensitive workflows until a full consolidation ADR is approved.

## Migration Safety Notes
- All new structures are additive.
- No destructive column/table drops in Phase 12.
- Existing report instances remain readable and updatable.
