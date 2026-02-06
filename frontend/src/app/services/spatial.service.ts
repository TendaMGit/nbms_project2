import { Injectable } from '@angular/core';

import { FeatureCollectionPayload, SpatialLayer } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class SpatialService {
  constructor(private readonly api: ApiClientService) {}

  layers() {
    return this.api.get<{ layers: SpatialLayer[] }>('spatial/layers');
  }

  features(
    slug: string,
    params: { bbox?: string; province?: string; indicator?: string; year?: number | undefined; limit?: number }
  ) {
    return this.api.get<FeatureCollectionPayload>(`spatial/layers/${slug}/features`, params);
  }
}
