import { Injectable } from '@angular/core';
import { Observable, of, shareReplay } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { AuthCapabilitiesResponse, AuthMeResponse } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private lastKnownMe: AuthMeResponse | null | undefined;

  constructor(private readonly api: ApiClientService) {}

  getMe(): Observable<AuthMeResponse | null> {
    return this.api.get<AuthMeResponse>('auth/me').pipe(
      tap((me) => {
        this.lastKnownMe = me;
      }),
      catchError(() => of(this.lastKnownMe ?? null)),
      shareReplay(1)
    );
  }

  getCsrfToken(): Observable<{ csrfToken: string }> {
    return this.api.get<{ csrfToken: string }>('auth/csrf');
  }

  getCapabilities(): Observable<AuthCapabilitiesResponse> {
    return this.api.get<AuthCapabilitiesResponse>('auth/capabilities');
  }
}
