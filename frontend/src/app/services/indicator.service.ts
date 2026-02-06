import { Injectable } from '@angular/core';

import {
  IndicatorDatasetsResponse,
  IndicatorDetailResponse,
  IndicatorListResponse,
  IndicatorSeriesResponse
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class IndicatorService {
  constructor(private readonly api: ApiClientService) {}

  list(filters: Record<string, string | number | undefined>) {
    return this.api.get<IndicatorListResponse>('indicators', filters);
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

  validation(uuid: string) {
    return this.api.get<{ overall_state: string; checks: Array<{ state: string; notes: string[] }> }>(
      `indicators/${uuid}/validation`
    );
  }
}
