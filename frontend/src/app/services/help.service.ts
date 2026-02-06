import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class HelpService {
  constructor(private readonly api: ApiClientService) {}

  getSections(): Observable<{ version: string; sections: Record<string, Record<string, string>> }> {
    return this.api
      .get<{ version: string; sections: Record<string, Record<string, string>> }>('help/sections')
      .pipe(shareReplay(1));
  }
}
