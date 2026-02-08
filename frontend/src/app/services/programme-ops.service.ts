import { Injectable, inject } from '@angular/core';

import { ApiClientService } from './api-client.service';
import { ProgrammeDetailResponse, ProgrammeRun, ProgrammeSummary } from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ProgrammeOpsService {
  private readonly api = inject(ApiClientService);

  list(search = '') {
    const params = new URLSearchParams();
    if (search.trim()) {
      params.set('search', search.trim());
    }
    return this.api.get<{ programmes: ProgrammeSummary[] }>(`programmes?${params.toString()}`);
  }

  detail(programmeUuid: string) {
    return this.api.get<ProgrammeDetailResponse>(`programmes/${programmeUuid}`);
  }

  run(programmeUuid: string, options: { run_type?: string; dry_run?: boolean; execute_now?: boolean } = {}) {
    return this.api.post<ProgrammeRun>(`programmes/${programmeUuid}/runs`, options);
  }

  rerun(runUuid: string) {
    return this.api.post<ProgrammeRun>(`programmes/runs/${runUuid}`, {});
  }

  runReport(runUuid: string) {
    return this.api.get<any>(`programmes/runs/${runUuid}/report`);
  }
}
