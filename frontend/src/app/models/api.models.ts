import type { Geometry } from 'geojson';

export interface AuthMeResponse {
  id: number;
  username: string;
  email: string;
  full_name: string;
  roles: string[];
  organisation: { id: number | null; name: string | null };
  capabilities: Record<string, boolean>;
}

export interface AuthCapabilitiesResponse {
  capabilities: Record<string, boolean>;
}

export interface DashboardSummary {
  counts: Record<string, number>;
  approvals_queue: number;
  latest_published_updates: IndicatorListItem[];
  data_quality_alerts: Array<{ indicator_uuid: string; indicator_code: string; issues: string[] }>;
  published_by_framework_target: Array<{
    framework_indicator__framework_target__framework__code: string;
    framework_indicator__framework_target__code: string;
    total: number;
  }>;
  approvals_over_time: Array<{ day: string; action: string; total: number }>;
  trend_signals: Array<{ indicator_uuid: string; indicator_code: string; trend: string }>;
}

export interface IndicatorListItem {
  uuid: string;
  code: string;
  title: string;
  description: string;
  indicator_type: string;
  status: string;
  sensitivity: string;
  qa_status: string;
  reporting_capability: string;
  national_target: { uuid: string | null; code: string | null; title: string | null };
  organisation: { id: number | null; name: string | null };
  last_updated_on: string | null;
  updated_at: string;
  tags: string[];
  method_readiness_state: string;
  method_types: string[];
  coverage: { geography: string; time_start_year: number | null; time_end_year: number | null };
}

export interface IndicatorListResponse {
  count: number;
  page: number;
  page_size: number;
  results: IndicatorListItem[];
  facets: Record<string, unknown>;
}

export interface IndicatorDetailResponse {
  indicator: IndicatorListItem;
  narrative?: {
    summary?: string;
    limitations?: string;
    spatial_coverage?: string;
    temporal_coverage?: string;
  };
  methodologies: Array<{
    methodology_code: string;
    methodology_title: string;
    version: string;
    effective_date: string | null;
    is_primary: boolean;
  }>;
  evidence: Array<{ uuid: string; title: string; evidence_type: string; source_url: string }>;
  series: Array<{ uuid: string; title: string; unit: string; value_type: string; status: string; sensitivity: string }>;
  method_profiles: Array<{
    uuid: string;
    method_type: string;
    implementation_key: string;
    readiness_state: string;
    readiness_notes: string;
    last_success_at: string | null;
  }>;
  spatial_readiness?: {
    overall_ready: boolean;
    layer_requirements: Array<{
      layer_code: string;
      title: string;
      available: boolean;
      sensitivity: string;
      consent_required: boolean;
      last_ingestion_status: string | null;
      last_ingestion_rows: number | null;
      last_ingestion_at: string | null;
    }>;
    source_requirements: Array<{
      code: string;
      title: string;
      status: string;
      last_sync_at: string | null;
      last_feature_count: number;
      requires_token: boolean;
      enabled_by_default: boolean;
    }>;
    disaggregation_expectations_json: Record<string, unknown>;
    cadence: string;
    notes: string;
    last_checked_at: string | null;
  };
  registry_readiness?: {
    overall_ready: boolean;
    checks: Array<{
      key: string;
      required: boolean;
      minimum: number;
      available: number;
    }>;
    notes: string;
    last_checked_at: string | null;
  };
  pipeline?: {
    data_last_refreshed_at: string | null;
    latest_year: number | null;
    latest_pipeline_run_uuid: string | null;
    latest_pipeline_run_status: string | null;
  };
  used_by_graph?: {
    indicator: { uuid: string; code: string; title: string };
    framework_targets: Array<{ framework_code: string | null; target_code: string | null; target_title: string | null }>;
    programmes: Array<{ uuid: string; programme_code: string; title: string }>;
    report_products: Array<{ code: string; title: string; version: string }>;
  };
}

export interface IndicatorMethodProfileResponse {
  indicator_uuid: string;
  profiles: Array<{
    uuid: string;
    method_type: string;
    implementation_key: string;
    summary: string;
    required_inputs_json: unknown[];
    disaggregation_requirements_json: unknown[];
    readiness_state: string;
    readiness_notes: string;
    last_run_at: string | null;
    last_success_at: string | null;
    recent_runs: Array<{
      uuid: string;
      status: string;
      started_at: string | null;
      finished_at: string | null;
      requested_by: string | null;
    }>;
  }>;
}

export interface IndicatorDatasetItem {
  uuid: string;
  title: string;
  status: string;
  sensitivity: string;
  organisation: string | null;
  note: string;
}

export interface IndicatorDatasetsResponse {
  indicator_uuid: string;
  datasets: IndicatorDatasetItem[];
}

export interface IndicatorSeriesResponse {
  indicator_uuid: string;
  aggregation: string;
  results: Array<{
    bucket: number | string;
    count: number;
    numeric_mean: number | null;
    values: Array<{
      year: number;
      value_numeric: number | null;
      value_text: string | null;
      disaggregation: Record<string, unknown>;
      spatial_resolution?: string;
      spatial_unit?: { uuid: string; unit_code: string; name: string } | null;
      spatial_layer?: { uuid: string; layer_code: string; title: string } | null;
    }>;
  }>;
}

export interface SpatialLayer {
  uuid: string;
  layer_code: string;
  name: string;
  title: string;
  slug: string;
  description: string;
  data_ref: string;
  theme: string;
  source_type: string;
  sensitivity: string;
  consent_required: boolean;
  export_approved: boolean;
  is_public: boolean;
  attribution: string;
  license: string;
  update_frequency: string;
  temporal_extent: Record<string, unknown>;
  default_style_json: Record<string, unknown>;
  publish_to_geoserver?: boolean;
  geoserver_layer_name?: string;
  indicator: { uuid: string; code: string; title: string } | null;
}

export interface IndicatorMapResponse extends FeatureCollectionPayload {
  indicator_uuid: string;
  indicator_code: string;
  year: number | null;
  layer_code?: string;
}

export interface FeatureCollectionPayload {
  type: 'FeatureCollection';
  numberMatched?: number;
  numberReturned?: number;
  limit?: number;
  offset?: number;
  features: Array<{
    type: 'Feature';
    id: string;
    geometry: Geometry;
    properties: Record<string, unknown>;
  }>;
}

export interface OgcCollectionList {
  collections: Array<{
    id: string;
    title: string;
    description: string;
    itemType: string;
  }>;
}

export interface TileJsonPayload {
  tilejson: string;
  name: string;
  description: string;
  attribution: string;
  tiles: string[];
  minzoom: number;
  maxzoom: number;
}

export interface EcosystemRegistryItem {
  uuid: string;
  ecosystem_code: string;
  name: string;
  realm: string;
  biome: string;
  bioregion: string;
  vegmap_version: string;
  get_node: string | null;
  status: string;
  sensitivity: string;
  qa_status: string;
  organisation: string | null;
  updated_at: string;
}

export interface EcosystemRegistryListResponse {
  count: number;
  page: number;
  page_size: number;
  results: EcosystemRegistryItem[];
}

export interface EcosystemRegistryDetailResponse {
  ecosystem: EcosystemRegistryItem & {
    vegmap_source_id: string;
    description: string;
  };
  crosswalks: Array<{
    uuid: string;
    get_code: string;
    get_level: number;
    get_label: string;
    confidence: number;
    review_status: string;
    is_primary: boolean;
    evidence: string;
    reviewed_by: string | null;
    reviewed_at: string | null;
  }>;
  risk_assessments: Array<{
    uuid: string;
    assessment_year: number;
    assessment_scope: string;
    category: string;
    criterion_a: string;
    criterion_b: string;
    criterion_c: string;
    criterion_d: string;
    criterion_e: string;
    review_status: string;
    assessor: string | null;
    reviewed_by: string | null;
    updated_at: string;
  }>;
}

export interface TaxonRegistryItem {
  uuid: string;
  taxon_code: string;
  scientific_name: string;
  canonical_name: string;
  taxon_rank: string;
  taxonomic_status: string;
  kingdom: string;
  family: string;
  genus: string;
  is_native: boolean | null;
  is_endemic: boolean;
  has_national_voucher_specimen: boolean;
  voucher_specimen_count: number;
  primary_source_system: string;
  status: string;
  sensitivity: string;
  qa_status: string;
  organisation: string | null;
  updated_at: string;
}

export interface TaxonRegistryListResponse {
  count: number;
  page: number;
  page_size: number;
  results: TaxonRegistryItem[];
}

export interface TaxonRegistryDetailResponse {
  taxon: TaxonRegistryItem & {
    classification: {
      kingdom: string;
      phylum: string;
      class_name: string;
      order: string;
      family: string;
      genus: string;
      species: string;
    };
    gbif_taxon_key: number | null;
    gbif_usage_key: number | null;
    gbif_accepted_taxon_key: number | null;
  };
  names: Array<{
    uuid: string;
    name: string;
    name_type: string;
    language: string;
    is_preferred: boolean;
  }>;
  source_records: Array<{
    uuid: string;
    source_system: string;
    source_ref: string;
    source_url: string;
    retrieved_at: string;
    payload_hash: string;
    licence: string;
    citation: string;
    is_primary: boolean;
  }>;
  vouchers: Array<{
    uuid: string;
    occurrence_id: string;
    institution_code: string;
    collection_code: string;
    catalog_number: string;
    basis_of_record: string;
    event_date: string | null;
    country_code: string;
    locality: string;
    decimal_latitude: number | null;
    decimal_longitude: number | null;
    has_sensitive_locality: boolean;
    sensitivity: string;
    status: string;
  }>;
}

export interface IasRegistryItem {
  uuid: string;
  taxon_uuid: string;
  taxon_code: string;
  scientific_name: string;
  country_code: string;
  establishment_means_code: string;
  degree_of_establishment_code: string;
  pathway_code: string;
  is_invasive: boolean;
  regulatory_status: string;
  latest_eicat: string | null;
  latest_seicat: string | null;
  status: string;
  sensitivity: string;
  qa_status: string;
  updated_at: string;
}

export interface IasRegistryListResponse {
  count: number;
  page: number;
  page_size: number;
  results: IasRegistryItem[];
}

export interface IasRegistryDetailResponse {
  profile: IasRegistryItem & {
    establishment_means_label: string;
    degree_of_establishment_label: string;
    pathway_label: string;
    habitat_types_json: string[];
  };
  checklist_records: Array<{
    uuid: string;
    source_dataset: string;
    source_identifier: string;
    country_code: string;
    is_alien: boolean;
    is_invasive: boolean;
    establishment_means_code: string;
    degree_of_establishment_code: string;
    pathway_code: string;
    retrieved_at: string | null;
  }>;
  eicat_assessments: Array<{
    uuid: string;
    category: string;
    mechanisms_json: string[];
    impact_scope: string;
    confidence: number;
    review_status: string;
    assessed_on: string | null;
    assessed_by: string | null;
    reviewed_by: string | null;
  }>;
  seicat_assessments: Array<{
    uuid: string;
    category: string;
    wellbeing_constituents_json: string[];
    activity_change_narrative: string;
    confidence: number;
    review_status: string;
    assessed_on: string | null;
    assessed_by: string | null;
    reviewed_by: string | null;
  }>;
}

export interface ProgrammeTemplateRow {
  uuid: string;
  template_code: string;
  title: string;
  description: string;
  domain: string;
  pipeline_definition_json: Record<string, unknown>;
  required_outputs_json: Array<Record<string, unknown>>;
  status: string;
  sensitivity: string;
  qa_status: string;
  organisation: string | null;
  updated_at: string;
  linked_programme_uuid?: string | null;
}

export interface TemplatePack {
  uuid: string;
  code: string;
  title: string;
  mea_code: string;
  version: string;
  description: string;
  section_count: number;
}

export interface TemplatePackSection {
  uuid: string;
  code: string;
  title: string;
  ordering: number;
  schema_json: Record<string, unknown>;
}

export interface TemplatePackResponseRow {
  section_code: string;
  section_title: string;
  response_json: Record<string, unknown>;
  updated_by: string | null;
  updated_at: string | null;
}

export interface TemplatePackValidationSummary {
  pack_code: string;
  instance_uuid: string;
  generated_at: string;
  overall_ready: boolean;
  qa_items: Array<{
    severity: string;
    section: string;
    field?: string;
    code: string;
    message: string;
  }>;
  sections: Array<{
    code: string;
    title: string;
    completion: number;
    missing_fields: string[];
    warning_count: number;
  }>;
}

export interface SystemHealthServiceStatus {
  service: string;
  status: string;
  detail?: string;
}

export interface SystemHealthSummary {
  overall_status: 'ok' | 'degraded';
  services: SystemHealthServiceStatus[];
  recent_failures: Array<{
    action: string;
    event_type: string;
    object_type: string;
    object_uuid: string | null;
    created_at: string;
  }>;
}

export interface ReportingInstanceSummary {
  uuid: string;
  cycle_code: string;
  cycle_title: string;
  version_label: string;
  status: string;
  frozen_at: string | null;
  readiness_status: string;
  readiness_score: number | null;
}

export interface ProgrammeSummary {
  uuid: string;
  programme_code: string;
  title: string;
  programme_type: string;
  refresh_cadence: string;
  scheduler_enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  lead_org: string | null;
  open_alert_count: number;
  latest_run_status: string | null;
  dataset_link_count: number;
  indicator_link_count: number;
}

export interface ProgrammeRunStep {
  ordering: number;
  step_key: string;
  step_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  details_json: Record<string, unknown>;
}

export interface ProgrammeRunArtefact {
  uuid: string;
  label: string;
  storage_path: string;
  media_type: string;
  checksum_sha256: string;
  size_bytes: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface ProgrammeRunQaResult {
  uuid: string;
  code: string;
  status: string;
  message: string;
  details_json: Record<string, unknown>;
  created_at: string;
}

export interface ProgrammeRun {
  uuid: string;
  run_type: string;
  trigger: string;
  status: string;
  dry_run: boolean;
  requested_by: string | null;
  started_at: string | null;
  finished_at: string | null;
  input_summary_json: Record<string, unknown>;
  output_summary_json: Record<string, unknown>;
  lineage_json: Record<string, unknown>;
  log_excerpt: string;
  error_message: string;
  created_at: string;
  artefacts?: ProgrammeRunArtefact[];
  qa_results?: ProgrammeRunQaResult[];
  report_url?: string;
  steps: ProgrammeRunStep[];
}

export interface ProgrammeAlert {
  uuid: string;
  severity: string;
  state: string;
  code: string;
  message: string;
  details_json: Record<string, unknown>;
  run_uuid: string | null;
  created_by: string | null;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

export interface ProgrammeDetailResponse {
  programme: ProgrammeSummary & {
    description: string;
    geographic_scope: string;
    taxonomic_scope: string;
    ecosystem_scope: string;
    consent_required: boolean;
    sensitivity_class: string | null;
    agreement_code: string | null;
    pipeline_definition_json: Record<string, unknown>;
    data_quality_rules_json: Record<string, unknown>;
    lineage_notes: string;
    website_url: string;
    operating_institutions: Array<{ id: number; name: string; org_code: string }>;
    partners: Array<{ id: number; name: string; org_code: string }>;
    stewards: Array<{ user_id: number; username: string; role: string; is_primary: boolean }>;
  };
  runs: ProgrammeRun[];
  alerts: ProgrammeAlert[];
  can_manage: boolean;
}

export interface Nr7BuilderSummary {
  instance: {
    uuid: string;
    cycle_code: string;
    cycle_title: string;
    version_label: string;
    status: string;
    frozen_at: string | null;
  };
  validation: {
    overall_ready: boolean;
    generated_at: string;
    qa_items: Array<{ severity: string; code: string; section: string; message: string }>;
    sections: Array<{
      code: string;
      title: string;
      required: boolean;
      state: string;
      completion: number;
      missing_fields: string[];
      incomplete_fields: string[];
    }>;
  };
  preview_payload: Record<string, unknown> | null;
  preview_error: string | null;
  links: Record<string, string>;
}

export interface ReportWorkspaceSection {
  uuid: string;
  section_code: string;
  section_title: string;
  ordering: number;
  response_json: Record<string, unknown>;
  current_version: number;
  current_content_hash: string;
  locked_for_editing: boolean;
  updated_by: string | null;
  updated_at: string | null;
  latest_revision_uuid: string | null;
  schema_json?: Record<string, unknown>;
}

export interface ReportWorkspaceSummary {
  instance: {
    uuid: string;
    cycle_code: string;
    cycle_title: string;
    version_label: string;
    report_title: string;
    country_name: string;
    status: string;
    is_public: boolean;
    focal_point_org: string;
    publishing_authority_org: string;
    finalized_at: string | null;
    final_content_hash: string;
  };
  pack: {
    code: string;
    title: string;
    version: string;
  };
  sections: ReportWorkspaceSection[];
  section_approvals: Array<{
    section_code: string;
    approved: boolean;
    approved_by: string | null;
    approved_at: string | null;
  }>;
  workflow: {
    uuid: string;
    status: string;
    current_step: string;
    locked: boolean;
    latest_content_hash: string;
    actions: Array<{
      uuid: string;
      action_type: string;
      actor: string | null;
      comment: string;
      created_at: string;
    }>;
  };
  validation: TemplatePackValidationSummary;
  preview_payload: Record<string, unknown>;
  latest_dossier: {
    uuid: string;
    storage_path: string;
    content_hash: string;
    manifest_json: Record<string, unknown>;
    created_at: string;
  } | null;
  capabilities: Record<string, boolean>;
}

export interface ReportSectionHistory {
  section_code: string;
  current_version: number;
  revisions: Array<{
    uuid: string;
    version: number;
    author: string | null;
    content_hash: string;
    parent_hash: string;
    note: string;
    created_at: string;
  }>;
  diff: {
    from_version: number;
    to_version: number;
    changed_keys: string[];
  } | null;
}

export interface ReportCommentThreadPayload {
  threads: Array<{
    uuid: string;
    json_path: string;
    status: string;
    created_by: string | null;
    created_at: string;
    resolved_at: string | null;
    resolved_by: string | null;
    comments: Array<{
      uuid: string;
      author: string | null;
      body: string;
      created_at: string;
    }>;
  }>;
}

export interface ReportSuggestionPayload {
  suggestions: Array<{
    uuid: string;
    base_version: number;
    patch_json: Record<string, unknown>;
    rationale: string;
    status: string;
    created_by: string | null;
    created_at: string;
    decided_by: string | null;
    decided_at: string | null;
    decision_note: string;
  }>;
}

export interface BirdieDashboardResponse {
  programme: ProgrammeSummary;
  site_reports: Array<{
    site_code: string;
    site_name: string;
    province_code: string;
    last_year: number | null;
    abundance_index: number | null;
    richness: number | null;
    trend: string;
  }>;
  species_reports: Array<{
    species_code: string;
    common_name: string;
    guild: string;
    last_year: number | null;
    last_value: number | null;
    trend: string;
  }>;
  map_layers: Array<{ slug: string; name: string; indicator_code: string | null }>;
  provenance: Array<{
    dataset_key: string;
    captured_at: string;
    payload_hash: string;
    source_endpoint: string;
  }>;
}

export interface ReportProductSummary {
  uuid: string;
  code: string;
  title: string;
  version: string;
  description: string;
}

export interface ReportProductPreviewResponse {
  template: { code: string; title: string; version: string };
  payload: Record<string, unknown>;
  html_preview: string;
  run_uuid: string;
}
