import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { SystemHealthSummary } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class SystemHealthService {
  constructor(private readonly api: ApiClientService) {}

  getSummary(): Observable<SystemHealthSummary> {
    return this.api.get<SystemHealthSummary>('system/health');
  }
}
