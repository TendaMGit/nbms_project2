import { Injectable } from '@angular/core';

import { type IndicatorDimensionsResponse, type IndicatorVisualProfile } from '../models/api.models';
import { IndicatorService } from './indicator.service';

@Injectable({ providedIn: 'root' })
export class IndicatorVisualProfileService {
  constructor(private readonly indicators: IndicatorService) {}

  getProfile(uuid: string) {
    return this.indicators.visualProfile(uuid);
  }

  getDimensions(uuid: string) {
    return this.indicators.dimensions(uuid);
  }

  getGlobalDimensions() {
    return this.indicators.globalDimensions();
  }
}

export type { IndicatorDimensionsResponse, IndicatorVisualProfile };
