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
