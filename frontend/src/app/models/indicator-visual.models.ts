import type {
  IndicatorCubeResponse,
  IndicatorDimension,
  IndicatorMapResponse,
  IndicatorSeriesResponse,
  IndicatorVisualProfile,
} from './api.models';
import type { NbmsContextPatch, NbmsContextQueryParams } from './context.models';

export type IndicatorViewKey = 'timeseries' | 'distribution' | 'taxonomy' | 'matrix' | 'binary';
export type IndicatorTopN = 20 | 50 | 100;

export interface IndicatorSeriesRequest {
  state: IndicatorViewRouteState | NbmsContextQueryParams;
  agg: string;
  groupBy?: string;
  overrides?: Partial<IndicatorAnalyticsQuery>;
}

export interface IndicatorCubeRequest {
  state: IndicatorViewRouteState;
  groupBy: string[];
  measure?: string;
  topN?: number;
  overrides?: Partial<IndicatorAnalyticsQuery>;
}

export interface IndicatorMapRequest {
  state: IndicatorViewRouteState;
  layer?: string;
  overrides?: Partial<IndicatorAnalyticsQuery>;
}

export interface IndicatorAnalyticsQuery {
  report_cycle?: string;
  release?: string;
  method?: string;
  geo_type?: string;
  geo_code?: string;
  start_year?: number;
  end_year?: number;
  agg?: string;
  metric?: string;
  published_only?: 0 | 1;
  group_by?: string;
  measure?: string;
  top_n?: number;
  dim?: string;
  dim_value?: string;
  tax_level?: string;
  tax_code?: string;
  compare?: string;
  left?: string;
  right?: string;
  layer_code?: string;
}

export interface IndicatorViewRouteState extends NbmsContextQueryParams {
  dim: string;
  dim_value: string;
  tax_level: string;
  tax_code: string;
  top_n: IndicatorTopN;
}

export type IndicatorViewRoutePatch = NbmsContextPatch &
  Partial<Pick<IndicatorViewRouteState, 'dim' | 'dim_value' | 'tax_level' | 'tax_code' | 'top_n'>>;

export interface IndicatorDimensionGroup {
  categorical: IndicatorDimension[];
  geographic: IndicatorDimension[];
  taxonomy: IndicatorDimension[];
}

export type IndicatorCubeRow = Record<string, unknown> & {
  value: number | null;
  count: number;
  statusFlags?: {
    has_uncertainty?: boolean;
    has_release?: boolean;
    has_spatial?: boolean;
  };
};

export interface IndicatorViewKpi {
  title: string;
  value: string;
  unit?: string;
  hint?: string;
  icon?: string;
  tone?: 'neutral' | 'positive' | 'negative' | 'info';
  accent?: boolean;
  deltaLabel?: string;
}

export interface IndicatorViewCallout {
  tone: 'info' | 'warning' | 'error';
  title: string;
  message: string;
}

export interface IndicatorViewSummary {
  kpis: IndicatorViewKpi[];
  callouts: IndicatorViewCallout[];
}

export interface IndicatorViewDataState<T> {
  loading: boolean;
  error: string | null;
  payload: T | null;
}

export type IndicatorSeriesPayload = IndicatorSeriesResponse;
export type IndicatorCubePayload = IndicatorCubeResponse;
export type IndicatorMapPayload = IndicatorMapResponse;
export type IndicatorVisualProfilePayload = IndicatorVisualProfile;
