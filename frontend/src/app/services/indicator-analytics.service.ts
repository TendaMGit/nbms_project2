import { Injectable } from '@angular/core';

import type {
  IndicatorCubeRequest,
  IndicatorMapRequest,
  IndicatorSeriesRequest,
  IndicatorAnalyticsQuery,
  IndicatorViewRouteState,
} from '../models/indicator-visual.models';
import type { NbmsContextQueryParams } from '../models/context.models';
import { IndicatorService } from './indicator.service';

@Injectable({ providedIn: 'root' })
export class IndicatorAnalyticsService {
  constructor(private readonly indicators: IndicatorService) {}

  getSeries(uuid: string, request: IndicatorSeriesRequest) {
    return this.indicators.series(uuid, {
      ...this.baseQuery(request.state),
      agg: request.agg,
      group_by: request.groupBy,
      ...request.overrides,
    });
  }

  getCube(uuid: string, request: IndicatorCubeRequest) {
    return this.indicators.cube(uuid, {
      ...this.baseQuery(request.state),
      group_by: request.groupBy.join(','),
      measure: request.measure || 'value',
      top_n: request.topN ?? request.state.top_n,
      ...request.overrides,
    });
  }

  getMap(uuid: string, request: IndicatorMapRequest) {
    return this.indicators.map(uuid, {
      ...this.baseQuery(request.state),
      layer_code: request.layer,
      ...request.overrides,
    });
  }

  private baseQuery(state: IndicatorViewRouteState | NbmsContextQueryParams): IndicatorAnalyticsQuery {
    return {
      report_cycle: state.report_cycle || undefined,
      release: state.release || undefined,
      method: state.method || undefined,
      geo_type: state.geo_type || undefined,
      geo_code: state.geo_code || undefined,
      start_year: state.start_year ?? undefined,
      end_year: state.end_year ?? undefined,
      agg: state.agg || undefined,
      metric: state.metric || undefined,
      published_only: state.published_only,
      dim: 'dim' in state ? state.dim || undefined : undefined,
      dim_value: 'dim_value' in state ? state.dim_value || undefined : undefined,
      tax_level: 'tax_level' in state ? state.tax_level || undefined : undefined,
      tax_code: 'tax_code' in state ? state.tax_code || undefined : undefined,
      top_n: 'top_n' in state ? state.top_n : undefined,
    };
  }
}
