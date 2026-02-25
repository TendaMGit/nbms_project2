import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { DashboardSummary } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  constructor(private readonly api: ApiClientService) {}

  getSummary() {
    return this.api.get<DashboardSummary>('dashboard/summary').pipe(
      catchError(() =>
        of({
          counts: {},
          approvals_queue: 0,
          latest_published_updates: [],
          data_quality_alerts: [],
          published_by_framework_target: [],
          approvals_over_time: [],
          trend_signals: [],
          indicator_readiness: {
            totals: { ready: 0, warning: 0, blocked: 0 },
            by_target: []
          }
        })
      )
    );
  }
}
