import { Injectable } from '@angular/core';

import { FeatureCollectionPayload, OgcCollectionList, SpatialLayer, TileJsonPayload } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class SpatialService {
  constructor(private readonly api: ApiClientService) {}

  layers() {
    return this.api.get<{ layers: SpatialLayer[] }>('spatial/layers');
  }

  collections() {
    return this.api.get<OgcCollectionList>('ogc/collections');
  }

  features(
    slug: string,
    params: {
      bbox?: string;
      province?: string;
      indicator?: string;
      year?: number | undefined;
      limit?: number;
      offset?: number;
      filter?: string;
      datetime?: string;
    }
  ) {
    return this.api.get<FeatureCollectionPayload>(`spatial/layers/${slug}/features`, params);
  }

  ogcItems(
    layerCode: string,
    params: { bbox?: string; limit?: number; offset?: number; filter?: string; datetime?: string }
  ) {
    return this.api.get<FeatureCollectionPayload>(`ogc/collections/${layerCode}/items`, params);
  }

  tileJson(layerCode: string) {
    return this.api.get<TileJsonPayload>(`tiles/${layerCode}/tilejson`);
  }

  exportGeoJson(layerCode: string, params: { bbox?: string; filter?: string; datetime?: string; limit?: number }) {
    return this.api.get<FeatureCollectionPayload>(`spatial/layers/${layerCode}/export.geojson`, params);
  }
}
