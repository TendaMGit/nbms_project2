import { Injectable } from '@angular/core';
import { of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { TemplatePack } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class TemplatePackService {
  constructor(private readonly api: ApiClientService) {}

  list() {
    return this.api.get<{ packs: TemplatePack[] }>('template-packs').pipe(
      catchError(() => of({ packs: [] }))
    );
  }
}
