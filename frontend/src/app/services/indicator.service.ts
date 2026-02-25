import { Injectable } from '@angular/core';

import {
  DiscoverySearchResponse,
  IndicatorDatasetsResponse,
  IndicatorDetailResponse,
  IndicatorListResponse,
  IndicatorMethodProfileResponse,
  IndicatorMapResponse,
  IndicatorSeriesResponse
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class IndicatorService {
  constructor(private readonly api: ApiClientService) {}

  list(filters: Record<string, string | number | undefined>) {
    return this.api.get<IndicatorListResponse>('indicators', filters);
  }

  discovery(search: string, limit = 8) {
    return this.api.get<DiscoverySearchResponse>('discovery/search', { search, limit });
  }

  detail(uuid: string) {
    return this.api.get<IndicatorDetailResponse>(`indicators/${uuid}`);
  }

  datasets(uuid: string) {
    return this.api.get<IndicatorDatasetsResponse>(`indicators/${uuid}/datasets`);
  }

  series(uuid: string, filters: Record<string, string | number | undefined>) {
    return this.api.get<IndicatorSeriesResponse>(`indicators/${uuid}/series`, filters);
  }

  map(uuid: string, filters: Record<string, string | number | undefined>) {
    return this.api.get<IndicatorMapResponse>(`indicators/${uuid}/map`, filters);
  }

  validation(uuid: string) {
    return this.api.get<{ overall_state: string; checks: Array<{ state: string; notes: string[] }> }>(
      `indicators/${uuid}/validation`
    );
  }

  methods(uuid: string) {
    return this.api.get<IndicatorMethodProfileResponse>(`indicators/${uuid}/methods`);
  }

  runMethod(uuid: string, profileUuid: string, payload: { params?: Record<string, unknown>; use_cache?: boolean } = {}) {
    return this.api.post<{
      run_uuid: string;
      status: string;
      output_json: Record<string, unknown>;
      error_message: string;
      profile_uuid: string;
      indicator_uuid: string;
    }>(`indicators/${uuid}/methods/${profileUuid}/run`, payload);
  }

  transitionReleaseWorkflow(
    seriesUuid: string,
    payload: { action: 'submit' | 'approve'; note?: string; sense_check_attested?: boolean }
  ) {
    return this.api.post<{
      series_uuid: string;
      status: string;
      workflow: Record<string, unknown>;
    }>(`indicator-series/${seriesUuid}/workflow`, payload);
  }
}
