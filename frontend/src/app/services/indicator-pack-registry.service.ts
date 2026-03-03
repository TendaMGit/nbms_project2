import { Injectable } from '@angular/core';
import { forkJoin, map } from 'rxjs';

import type { IndicatorPackDescriptor } from '../models/indicator-pack.models';
import { IndicatorVisualProfileService } from './indicator-visual-profile.service';

@Injectable({ providedIn: 'root' })
export class IndicatorPackRegistryService {
  constructor(private readonly profiles: IndicatorVisualProfileService) {}

  getPack(uuid: string) {
    return forkJoin({
      profile: this.profiles.getProfile(uuid),
      dimensionsResponse: this.profiles.getDimensions(uuid),
    }).pipe(
      map(({ profile, dimensionsResponse }): IndicatorPackDescriptor => ({
        indicatorUuid: uuid,
        packId: profile.packId || 'unclassified',
        packLabel: profile.packLabel || 'Indicator pack',
        profile,
        dimensions: dimensionsResponse.dimensions,
      })),
    );
  }
}

