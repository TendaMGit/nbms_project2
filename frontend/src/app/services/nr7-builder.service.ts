import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Nr7BuilderSummary, ReportingInstanceSummary } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class Nr7BuilderService {
  constructor(private readonly api: ApiClientService) {}

  listInstances(): Observable<{ instances: ReportingInstanceSummary[] }> {
    return this.api.get<{ instances: ReportingInstanceSummary[] }>('reporting/instances');
  }

  getSummary(instanceUuid: string): Observable<Nr7BuilderSummary> {
    return this.api.get<Nr7BuilderSummary>(`reporting/instances/${instanceUuid}/nr7/summary`);
  }

  getPdfUrl(instanceUuid: string): string {
    return `/api/reporting/instances/${instanceUuid}/nr7/export.pdf`;
  }
}
