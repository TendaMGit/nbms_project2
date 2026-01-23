# Target Model Plan (Registry Layer)

This plan describes the **future** registry models to be added to
`nbms_project2`. No schema changes are made in PR-1.

## Recommended approach for GBF goals

**Option A (preferred): FrameworkGoal table, FrameworkTarget FK -> FrameworkGoal**
- Pros:
  - Matches GBF structure and supports goal-level reporting.
  - Keeps goals distinct from targets and avoids overloading target typing.
- Cons:
  - Adds one additional registry table.

**Option B: represent goals as targets with a type flag**
- Pros:
  - Fewer tables.
- Cons:
  - Blurs semantics (goal vs target) and complicates mapping logic.

**Recommendation:** Option A.

## Proposed registry models (future PRs)

> Model names are illustrative; use naming conventions already established in
> `nbms_project2`.

### MonitoringProgramme
- **Key fields:** uuid, programme_code, title, description, programme_type,
  lead_org (FK Organisation), partner_orgs (M2M Organisation),
  geographic_scope, objectives, sampling_design_summary, update_frequency,
  qa_process_summary, is_active, source_system, source_ref, notes
- **Lifecycle states:** Draft / Published / Retired
- **ABAC hooks:** organisation-based visibility + lifecycle status
- **Consent/sensitivity:** reference to SensitivityClass + consent_required flag
- **Audit/provenance:** created_by, created_at, updated_at, source_system, source_ref

### DatasetCatalog (registry, separate from approved Dataset/DatasetRelease)
- **Key fields:** uuid, dataset_code, title, description, dataset_type,
  custodian_org, producer_org, licence, access_level, sensitivity_code,
  consent_required, agreement_code, temporal_start/end, update_frequency,
  spatial_coverage_description, spatial_resolution, taxonomy_standard,
  ecosystem_classification, doi_or_identifier, landing_page_url,
  api_endpoint_url, file_formats, qa_status, citation, keywords,
  last_updated_date, is_active, source_system, source_ref
- **Lifecycle states:** Draft / Published / Retired
- **ABAC hooks:** access_level + sensitivity + organisation
- **Consent/sensitivity:** ties to SensitivityClass and DataAgreement
- **Audit/provenance:** created_by, created_at, updated_at, source_system, source_ref

### Methodology
- **Key fields:** uuid, methodology_code, title, description, owner_org,
  scope, references_url, is_active, source_system, source_ref
- **Lifecycle states:** Draft / Published / Retired
- **ABAC hooks:** owner organisation + status
- **Consent/sensitivity:** typically not sensitive; allow classification if needed
- **Audit/provenance:** created_by, created_at, updated_at, source_system, source_ref

### MethodologyVersion
- **Key fields:** uuid, methodology (FK), version, status, effective_date,
  deprecated_date, change_log, protocol_url, computational_script_url,
  parameters_json, qa_steps_summary, peer_reviewed, approval_body,
  approval_reference, is_active, source_system, source_ref
- **Lifecycle states:** Draft / Active / Deprecated
- **ABAC hooks:** inherits from Methodology
- **Consent/sensitivity:** use SensitivityClass only if required
- **Audit/provenance:** created_by, created_at, updated_at, source_system, source_ref

### Organisation (registry augmentation)
- **Key fields:** org_uuid, org_code, org_name, org_type, parent_org_code,
  website_url, primary_contact_name/email, alt_contact_name/email,
  is_active, source_system, source_ref
- **Note:** `nbms_project2` already has `Organisation` for user accounts. This
  plan assumes either extending it **or** adding a separate registry model.

### SensitivityClass
- **Key fields:** sensitivity_code, sensitivity_name, description,
  access_level_default, consent_required_default, redaction_policy,
  legal_basis, is_active, source_system, source_ref
- **Lifecycle states:** Draft / Published / Retired
- **ABAC hooks:** public by default (classification list)

### DataAgreement
- **Key fields:** agreement_uuid, agreement_code, title, agreement_type,
  parties_org_codes, start_date, end_date, status, licence, restrictions_summary,
  benefit_sharing_terms, citation_requirement, document_url, is_active,
  source_system, source_ref
- **Lifecycle states:** Draft / Active / Expired / Retired
- **ABAC hooks:** restricted by organisation + security officer roles
- **Consent/sensitivity:** agreement may impose consent/usage constraints

### Link tables (registry mapping)
- Programme <-> Dataset
- Programme <-> Indicator
- Methodology <-> Dataset
- Methodology <-> Indicator

**Fields (recommended):**
- left_code/uuid, right_code/uuid
- relationship_type / role
- notes, is_active, source_system, source_ref

## Import/export approach (planned for PR-2/PR-3)

- Idempotent CSV upsert commands (by code/uuid)
- Validation + rejection logs per row
- Referential integrity checks (org codes, agreement codes, sensitivity codes)
- No secrets in CSV; documents referenced by URL only

## Reporting readiness/completeness metrics (planned)

- For each indicator: linked national target(s), mapped framework indicator(s)
- Monitoring programme coverage per indicator
- Dataset catalog coverage per indicator
- Methodology version coverage per indicator
- Agreement/sensitivity completeness for datasets and programmes
