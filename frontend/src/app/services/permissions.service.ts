import { Injectable, inject } from '@angular/core';
import { Observable, map, shareReplay } from 'rxjs';

import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class PermissionsService {
  private readonly auth = inject(AuthService);

  readonly capabilities$ = this.auth.getCapabilities().pipe(
    map((payload) => payload.capabilities ?? {}),
    shareReplay(1)
  );

  has$(capability: string): Observable<boolean> {
    return this.capabilities$.pipe(map((capabilities) => Boolean(capabilities[capability])));
  }
}
