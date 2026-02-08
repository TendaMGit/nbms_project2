import { Injectable } from '@angular/core';

import {
  EcosystemRegistryDetailResponse,
  EcosystemRegistryListResponse,
  IasRegistryDetailResponse,
  IasRegistryListResponse,
  TaxonRegistryDetailResponse,
  TaxonRegistryListResponse,
  ProgrammeTemplateRow
} from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class RegistryService {
  constructor(private readonly api: ApiClientService) {}

  listEcosystems(params: Record<string, string | number | boolean | undefined>) {
    return this.api.get<EcosystemRegistryListResponse>('registries/ecosystems', params);
  }

  ecosystemDetail(uuid: string) {
    return this.api.get<EcosystemRegistryDetailResponse>(`registries/ecosystems/${uuid}`);
  }

  listTaxa(params: Record<string, string | number | boolean | undefined>) {
    return this.api.get<TaxonRegistryListResponse>('registries/taxa', params);
  }

  taxonDetail(uuid: string) {
    return this.api.get<TaxonRegistryDetailResponse>(`registries/taxa/${uuid}`);
  }

  listIas(params: Record<string, string | number | boolean | undefined>) {
    return this.api.get<IasRegistryListResponse>('registries/ias', params);
  }

  iasDetail(uuid: string) {
    return this.api.get<IasRegistryDetailResponse>(`registries/ias/${uuid}`);
  }

  programmeTemplates(params: Record<string, string | number | boolean | undefined> = {}) {
    return this.api.get<{ templates: ProgrammeTemplateRow[] }>('programmes/templates', params);
  }
}
