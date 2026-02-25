import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs/operators';

import { AuthService } from '../services/auth.service';

export function requireCapability(capability: string): CanActivateFn {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);
    return authService.getMe().pipe(
      map((me) => {
        if (!me) {
          if (typeof window !== 'undefined') {
            const next = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.assign(`/account/login/?next=${next}`);
          }
          return false;
        }
        if (me?.capabilities?.[capability]) {
          return true;
        }
        return router.createUrlTree(['/indicators']);
      })
    );
  };
}
