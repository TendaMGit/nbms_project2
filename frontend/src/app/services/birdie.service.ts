import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { BirdieDashboardResponse } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class BirdieService {
  constructor(private readonly api: ApiClientService) {}

  dashboard() {
    return this.api.get<BirdieDashboardResponse>('integrations/birdie/dashboard').pipe(
      catchError(() =>
        of({
          programme: {
            uuid: '',
            programme_code: '',
            title: '',
            programme_type: '',
            refresh_cadence: '',
            scheduler_enabled: false,
            next_run_at: null,
            last_run_at: null,
            lead_org: null,
            open_alert_count: 0,
            latest_run_status: null,
            dataset_link_count: 0,
            indicator_link_count: 0
          },
          site_reports: [],
          species_reports: [],
          map_layers: [],
          provenance: []
        } as BirdieDashboardResponse)
      )
    );
  }
}
