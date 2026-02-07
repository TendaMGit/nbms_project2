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
    }>;
  }>;
}

export interface SpatialLayer {
  uuid: string;
  name: string;
  slug: string;
  description: string;
  source_type: string;
  sensitivity: string;
  is_public: boolean;
  default_style_json: Record<string, unknown>;
  indicator: { uuid: string; code: string; title: string } | null;
}

export interface FeatureCollectionPayload {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    id: string;
    geometry: Geometry;
    properties: Record<string, unknown>;
  }>;
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
