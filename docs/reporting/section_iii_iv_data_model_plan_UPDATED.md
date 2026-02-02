# ORT NR7 Sections I–V Structured Storage Plan (NBMS Project 2)

**Purpose:** Make Sections I–V of the CBD Online Reporting Tool (ORT) “National Report” implementation **exact**, **export-safe**, and **governance-safe** in NBMS Project 2, by ensuring we store the *right fields* in *structured models* (not just free text), while preserving existing workflows (approvals, ABAC/consent, readiness, deterministic exports).

This document is written as an **implementation prompt for agent**.  
It updates/extends the earlier “Section III/IV data model plan” to cover **Sections I–V** and to **enrich Section III/IV + Binary Indicators** so the ORT NR7 v2 export can be fully populated and stable.

---

## Non‑negotiable constraints (repeat in PR body)
1. **Windows-first local dev** (local Postgres), `ENABLE_GIS=false`, no GDAL, no Docker required.
2. **ABAC + consent** everywhere: never leak existence/metadata of objects the user cannot see.
3. **Deterministic ordering**: stable sort for coverage outputs, UI lists, review pack, and ORT NR7 v2 export.
4. **Backward compatible**: existing narrative storage must keep working; new structured models should not break existing instances.
5. **Minimal migrations**: add only what is needed; keep migrations reviewable and scoped.

---

## Reality check: what NBMS Project 2 already has (do not re‑implement)
- Reporting core: `ReportingCycle`, `ReportingInstance`, approvals, freeze, readiness, snapshots, review pack v2.
- Narrative storage: `ReportSectionTemplate` + `ReportSectionResponse` (generic Section I–V text capture).
- Structured storage exists for **Section III & IV progress** (current models):  
  `SectionIIINationalTargetProgress`, `SectionIVFrameworkTargetProgress`.
- Binary indicators exist: `BinaryIndicatorQuestion` + `BinaryIndicatorResponse` + seed command.
- ORT NR7 v2 exporter exists and is gated/deterministic already; do not change output unless the new structured fields are mapped intentionally.

**Implementation strategy:** extend what exists; add small, explicit models for Section I/II/V and a goal‑level model for Section IV; enrich III/IV progress + binary indicator metadata to match ORT question structure.

---

## Canonical ORT semantics by section (field‑level)

### Section I — Information on the report and process
**We need instance-scoped, structured metadata** (not only narrative) so export is complete and repeatable.

Create model: `SectionIReportContext` (1:1 with `ReportingInstance`)

| Field | Type | Required | Notes |
|---|---|---:|---|
| reporting_party_name | CharField(255) | yes | e.g., “South Africa”. Consider defaulting from country config but store snapshot value. |
| submission_language | CharField(64) | yes | e.g., “English”. Prefer code + label if ORT expects code. |
| additional_languages | JSONField(list[str]) | no | Free list; ORT allows “other languages”. |
| responsible_authorities | TextField | no | e.g., DFFE; can be multi-line. |
| contact_name | CharField(255) | no | ORT contact person. |
| contact_email | EmailField | no | ORT contact email. |
| preparation_process | TextField | no | “How was the report prepared?” narrative. |
| preparation_challenges | TextField | no | Constraints/limitations narrative. |
| acknowledgements | TextField | no | Contributors/partners narrative (organisations, people). |
| updated_at / updated_by | DateTime/FK(User) | yes | Auditable edit stamp. |

**UI**: A dedicated page under the instance (staff + instance ABAC) that edits this model, not generic section text.

---

### Section II — NBSAP update / adoption status + monitoring system description
Create model: `SectionIINBSAPStatus` (1:1 with `ReportingInstance`)


#### Spec corrections (ORT exactness patches)
- Q1 expected completion date is required when update status is **no** or **in progress**.
- Stakeholder group picklist must include `local_and_subnational_government` and `other_stakeholders`.
- Q3 adoption: when status is **no** or **other**, capture free-text "specify" and an expected adoption date.

#### 1) Updated NBSAP published (status)
| Field | Type | Required | Allowed values / rules |
|---|---|---:|---|
| nbsap_updated_status | CharField | yes | Enum: `yes`, `no`, `in_progress`, `other`, `unknown` |
| nbsap_updated_other_text | TextField | conditional | required if status=`other` |
| nbsap_expected_completion_date | DateField | conditional | required if status=`no` or `in_progress` (null allowed if unknown, but UI should warn) |

#### 2) Stakeholders involved in NBSAP update
| Field | Type | Required | Notes |
|---|---|---:|---|
| stakeholders_involved | CharField | yes | Enum: `yes`, `no`, `unknown` |
| stakeholder_groups | JSONField(list[str]) | conditional | if `stakeholders_involved=yes` store codes, see list below |
| stakeholder_groups_other_text | TextField | conditional | if selected “Other”, capture details |
| stakeholder_groups_notes | TextField | no | Optional narrative expansion |

**Stakeholder group codes** (from the Section II template):
- `women`, `youth`, `indigenous_and_local_communities`, `private_sector`, `scientific_community`, `civil_society_organizations`, `local_and_subnational_government`, `other_stakeholders`, `other`

#### 3) NBSAP formally adopted
| Field | Type | Required | Rules |
|---|---|---:|---|
| nbsap_adopted_status | CharField | yes | Enum: `yes`, `no`, `in_progress`, `other`, `unknown` |
| nbsap_adopted_other_text | TextField | conditional | if status=`no` or `other` (use as "specify") |
| nbsap_adoption_mechanism | TextField | conditional | required if status=`yes` or `in_progress` (capture “how”) |
| nbsap_expected_adoption_date | DateField | conditional | required if status=`no`, `other`, or `in_progress` (nullable with warning) |

#### 4) National biodiversity monitoring system description
| Field | Type | Required | Notes |
|---|---|---:|---|
| monitoring_system_description | TextField | yes | The narrative description required in Section II. |
| updated_at / updated_by | DateTime/FK(User) | yes | Auditable edit stamp. |

---

### Section III — Progress towards national targets (per NationalTarget)
**Existing model:** `SectionIIINationalTargetProgress` (ReportingInstance + NationalTarget unique).  
**Required enrichment:** align fields with actual ORT prompts.

Add/confirm the following fields on `SectionIIINationalTargetProgress`:

| Field | Type | Required | ORT mapping |
|---|---|---:|---|
| progress_level | CharField | yes | “Please indicate current level of progress” (enum below) |
| actions_taken | TextField | no | “Briefly describe main actions taken…” |
| progress_summary | TextField | yes | “Provide a narrative summary of progress…” |
| outcomes | TextField | no | “main outcomes achieved” (keep as separate if you already have it) |
| challenges_and_approaches | TextField | no | “Provide a summary of key challenges and approaches…” |
| effectiveness_examples | TextField | no | “Provide examples/cases… include links/attachments” |
| sdg_and_other_agreements | TextField | no | “Briefly describe relation to SDGs and other agreements…” |
| support_needed | TextField | no | **NBMS extension** (keep; not always in ORT templates) |
| period_start / period_end | DateField | no | useful for time-bounding claims |
| updated_at / updated_by | DateTime/FK(User) | yes | audit stamp |

**Progress level enum** (must match wording in ORT template as closely as possible):
- `on_track`
- `insufficient_rate`
- `no_change`
- `not_applicable`
- `unknown`
- `achieved`

**Linkages (already exist conceptually; enforce consistently)**
- M2M to `IndicatorDataSeries` (evidence for quantitative progress)
- M2M to `BinaryIndicatorResponse` (where national targets map to binary indicators)
- M2M to `Evidence` and/or `DatasetRelease`
- Optional M2M to `FrameworkTarget` (to show which global targets this national target contributes to)

**Deterministic ordering**
- Always sort target lists by `(code, title, uuid)` (lexicographic code; document that T1 < T10 < T2 behavior is expected).

---

### Section IV — Progress towards global goals and targets (GBF Goal A–D + GBF Targets)
Section IV has **two** layers that ORT commonly expects:
1) **2050 Goals** narrative (Goal A–D)  
2) **Global targets / binary indicators** (largely binary and comments)

#### A) 2050 Goal progress (per FrameworkGoal)
Create model: `SectionIVFrameworkGoalProgress` (ReportingInstance + FrameworkGoal unique)

| Field | Type | Required | Notes |
|---|---|---:|---|
| framework_goal | FK FrameworkGoal | yes | GBF goal record (A–D). |
| progress_summary | TextField | yes | “Summary of national progress contributing to the goal.” |
| actions_taken | TextField | no | Optional but useful. |
| outcomes | TextField | no | Optional. |
| challenges_and_approaches | TextField | no | Optional. |
| sdg_and_other_agreements | TextField | no | Optional. |
| evidence | M2M Evidence | no | Optional supporting evidence. |
| updated_at / updated_by | DateTime/FK(User) | yes | Audit stamp. |

#### B) Framework target progress (per FrameworkTarget) — keep existing, but align fields
**Existing model:** `SectionIVFrameworkTargetProgress` (ReportingInstance + FrameworkTarget unique).  
Align its fields to match Section III semantics (same naming) so exporter/UI can render both with shared partials.

Minimum field set on `SectionIVFrameworkTargetProgress`:
- `progress_summary` (required)
- `actions_taken` (optional)
- `outcomes` (optional)
- `challenges_and_approaches` (optional)
- `effectiveness_examples` (optional)
- `sdg_and_other_agreements` (optional)
- `support_needed` (optional, NBMS extension)
- plus existing M2M links: series, binary responses, evidence, dataset releases

**Important:** Do not assume every global target will have narrative text; many are represented via binary indicators + comments.

---

### Section V — Conclusions and additional information (instance level)
Create model: `SectionVConclusions` (1:1 with `ReportingInstance`)

| Field | Type | Required | Notes |
|---|---|---:|---|
| overall_assessment | TextField | yes | “Provide a summary overall assessment…” |
| decision_15_8_information | TextField | no | other information requested under decision 15/8 |
| decision_15_7_information | TextField | no | other information requested under decision 15/7 |
| decision_15_11_information | TextField | no | other information requested under decision 15/11 |
| plant_conservation_information | TextField | no | optional (e.g., plant conservation approaches) |
| additional_notes | TextField | no | catch-all |
| evidence | M2M Evidence | no | supporting documents |
| updated_at / updated_by | DateTime/FK(User) | yes | Audit stamp |

---

## Binary indicators — required enrichment (so Section IV is “exact”)

### Why this is required
The ORT represents many Section IV target questions as **binary indicator groups** (with numbered questions like “B.1”, “B.2”, etc.) plus a **group-level Comments** box. We need our binary indicator store to preserve:
- ORT keys (stable identifiers),
- question numbering and type,
- options and validations,
- group → target linkage,
- group comments,
- deterministic ordering.

### Target model shape (inspect existing models first)
**If models already contain equivalents, map to them and avoid churn. Otherwise implement:**

#### Model: `BinaryIndicatorGroup`
| Field | Type | Required | Notes |
|---|---|---:|---|
| key | CharField(64), unique | yes | e.g., `b.b` / `1.b` etc (ORT group key) |
| framework_target | FK FrameworkTarget | no | preferred; otherwise store `target_code` text and resolve later |
| binary_indicator_id | CharField(64) | no | ORT binary indicator identifier if provided |
| title | CharField(255) | no | optional label |
| ordering | IntegerField | no | stable ordering if ORT provides; else derived |
| source_ref | CharField(255) | no | e.g., ORT version / file |
| is_active | BooleanField | yes | soft disable |
| created_at/updated_at | DateTime | yes | audit |
Indexes: `(framework_target, key)`

#### Model: `BinaryIndicatorQuestion` (enrich existing)
Add/confirm fields (minimal but sufficient):
| Field | Type | Required | Notes |
|---|---|---:|---|
| group | FK BinaryIndicatorGroup | yes | group membership |
| key | CharField(128), unique | yes | stable ORT question key (not display number) |
| section | CharField(8) | yes | `A`/`B`/`C` (as in ORT template) |
| number | CharField(16) | yes | e.g., `B.1` |
| question_type | CharField(16) | yes | `single`, `multiple`, `text` |
| prompt | TextField | yes | the question text |
| options | JSONField | conditional | required for single/multiple |
| mandatory | BooleanField | yes | ORT required flag |
| validations | JSONField | no | min/max, mutually exclusive options, etc |
| is_active | BooleanField | yes | soft disable |

#### Model: `BinaryIndicatorGroupResponse`
| Field | Type | Required | Notes |
|---|---|---:|---|
| reporting_instance | FK ReportingInstance | yes | |
| group | FK BinaryIndicatorGroup | yes | |
| comments | TextField | no | the group-level ORT “Comments” field |
Unique: `(reporting_instance, group)`

#### Model: `BinaryIndicatorResponse` (question-level response; already exists)
Ensure it can store both:
- single-choice answer (one option)
- multi-choice answers (list of options)
- text answers (for `question_type=text`)
and is unique per `(reporting_instance, question)`.

### Seeding & versioning (Codex must implement idempotently)
- Extend existing seed command (or create a new one) to load groups + questions from **ORT app-data JSON** (you already have local notes for NR7 files).
- Must be re-runnable without duplication (upsert by `group.key` and `question.key`).
- Store a `source_ref` / version string so we can track ORT schema drift.

### Deterministic ordering
- Order groups by `(framework_target.code, group.key)`
- Order questions by `(section, number, key)` within group
- Ensure export uses this ordering.

---

## Export mapping (ORT NR7 v2)
**Goal:** ORT NR7 v2 export should draw from structured models when present, otherwise fall back to existing narrative responses.

Implementation rules:
1. **Section I:** export from `SectionIReportContext` (fallback: `ReportSectionResponse` for section I template).
2. **Section II:** export from `SectionIINBSAPStatus` (fallback: narrative response).
3. **Section III:** export from `SectionIIINationalTargetProgress` (must include progress_level + progress_summary at minimum).
4. **Section IV:** export goal narratives from `SectionIVFrameworkGoalProgress`; export binary indicator groups from group/question responses; target narratives from `SectionIVFrameworkTargetProgress` where required by your exporter.
5. **Section V:** export from `SectionVConclusions`.

**Do not change** any existing JSON keys used by the current exporter unless you are also updating golden tests and explicitly intend the change.

---

## UI / routes (minimal, consistent with current patterns)
All views must be staff-only + instance-scoped ABAC, consistent with review dashboard and readiness pages.

Add instance-scoped edit pages:
- `/reporting/instances/<uuid>/section-i/`
- `/reporting/instances/<uuid>/section-ii/`
- `/reporting/instances/<uuid>/section-v/`
- Add Section IV goal pages either:
  - integrated into `/reporting/instances/<uuid>/section-iv/` (preferred), or
  - `/reporting/instances/<uuid>/section-iv/goals/`

Keep existing Section III/IV pages; update templates/forms to use new fields (progress_summary, challenges_and_approaches, sdg_and_other_agreements, effectiveness_examples) without breaking existing data.

---

## Migrations and backward compatibility
- Add new models for Section I/II/IV-goals/V and binary indicator groups/responses **only if not already present**.
- For renamed fields (e.g., `summary` → `progress_summary`), prefer:
  1) keep DB field as `summary` but expose property alias `progress_summary`, OR
  2) add new field and keep old one, migrate data forward (explicit migration).

Be explicit and conservative—avoid destructive migrations.

---

## Tests (must be added/updated)
1. **Model + form validation** for Section II conditional fields:
   - if `nbsap_updated_status=in_progress`, completion date required (or at least warning enforced).
   - stakeholder_groups required when stakeholders_involved=yes.
2. **Non-leakage tests** for binary indicator group/coverage and Section III/IV linkages:
   - hidden targets/indicators should not show up and should not be counted.
3. **Exporter tests**:
   - extend golden tests only when you intentionally map new fields into export.
4. **UI tests**:
   - staff-only + instance ABAC enforced for new Section I/II/V edit pages.
5. Run full suite on Windows posture (`ENABLE_GIS=false`).

---

## Implementation order (recommended PR slicing)
- **PR 1:** Models + migrations + seed updates for Section I/II/V and BinaryIndicatorGroup(+Response). (No exporter changes yet.)
- **PR 2:** Update Section III/IV progress models + forms/templates to match ORT prompts + add Section IV goal progress UI.
- **PR 3:** Wire exporter to structured models + update golden tests intentionally.

Keep PRs reviewable; run full tests each PR.

---

## Codex “Definition of Done” checklist
- [ ] Section I/II/V structured models exist + edit UI works
- [ ] Section III/IV progress models capture ORT-required prompts (progress level, summaries, SDG linkages, examples)
- [ ] Binary indicator groups/questions/responses support ORT numbering + comments
- [ ] ABAC/consent enforced; no leakage
- [ ] Deterministic ordering documented + tested
- [ ] Export uses structured models (or falls back cleanly)
- [ ] Full test suite passes on Windows posture (`ENABLE_GIS=false`)
