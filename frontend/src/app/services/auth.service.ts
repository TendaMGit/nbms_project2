import { Injectable } from '@angular/core';
import { Observable, of, shareReplay } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthMeResponse } from '../models/api.models';
import { ApiClientService } from './api-client.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private readonly api: ApiClientService) {}

  getMe(): Observable<AuthMeResponse | null> {
    return this.api.get<AuthMeResponse>('auth/me').pipe(
      catchError(() => of(null)),
      shareReplay(1)
    );
  }

  getCsrfToken(): Observable<{ csrfToken: string }> {
    return this.api.get<{ csrfToken: string }>('auth/csrf');
  }
}
