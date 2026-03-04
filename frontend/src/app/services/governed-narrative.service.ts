import { Injectable } from '@angular/core';

import {
  GovernedNarrativeResponse,
  GovernedNarrativeVersionsResponse
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

export type GovernedNarrativeEntityType = 'dashboard' | 'framework' | 'target' | 'indicator';

@Injectable({ providedIn: 'root' })
export class GovernedNarrativeService {
  constructor(private readonly api: ApiClientService) {}

  get(entityType: GovernedNarrativeEntityType, entityId: string) {
    return this.api.get<GovernedNarrativeResponse>(`narratives/${entityType}/${encodeURIComponent(entityId)}`);
  }

  saveDraft(
    entityType: GovernedNarrativeEntityType,
    entityId: string,
    payload: {
      title?: string;
      entity_label?: string;
      provenance_url?: string;
      sections: Array<{ id: string; title: string; body: string }>;
    }
  ) {
    return this.api.post<GovernedNarrativeResponse>(`narratives/${entityType}/${encodeURIComponent(entityId)}/draft`, payload);
  }

  submit(
    entityType: GovernedNarrativeEntityType,
    entityId: string,
    payload: {
      title?: string;
      entity_label?: string;
      provenance_url?: string;
      sections: Array<{ id: string; title: string; body: string }>;
    }
  ) {
    return this.api.post<GovernedNarrativeResponse>(`narratives/${entityType}/${encodeURIComponent(entityId)}/submit`, payload);
  }

  versions(entityType: GovernedNarrativeEntityType, entityId: string) {
    return this.api.get<GovernedNarrativeVersionsResponse>(
      `narratives/${entityType}/${encodeURIComponent(entityId)}/versions`
    );
  }
}
