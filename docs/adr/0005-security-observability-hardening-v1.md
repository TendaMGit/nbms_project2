# ADR 0005: Security and Observability Hardening V1

- Status: Accepted
- Date: 2026-02-06

## Context

NBMS moved to a Docker-first full-stack runtime with Angular as primary UX and expanded `/api/*` surface. Governance requirements require stronger operational controls:

- end-to-end request traceability,
- hardened default security headers and session handling,
- practical abuse controls (rate limiting),
- operator-visible runtime health,
- CI-integrated security scanning.

## Decision

1. Introduce request correlation via `X-Request-ID`.
- Add backend middleware to propagate/generate IDs and set response headers.
- Forward request IDs through frontend nginx proxy.
- Inject request IDs into logs via logging filter.

2. Add security header middleware and production CSP baseline.
- Configure CSP in `config.settings.prod`.
- Attach CSP and nosniff headers via middleware to avoid proxy-only coupling.

3. Mitigate session fixation by one-time post-auth session rekey.
- Cycle session key once per authenticated session via middleware flag.

4. Expand rate-limit policy set in settings.
- Keep existing login/review limits.
- Add export/public-api/metrics limits with conservative defaults.

5. Add operator-facing health endpoint and UI.
- `GET /api/system/health` for staff/system-admin users.
- Angular “System Health” page consumes endpoint.

6. Expand CI security baseline.
- Bandit SAST (high-severity/high-confidence threshold).
- Trivy filesystem and backend image scans.
- Keep pip-audit and gitleaks.

## Consequences

Positive:
- Improved incident triage and auditability through request correlation.
- Better default protection against common web attacks and abusive request patterns.
- Operators can detect service degradation from the primary UI.
- Security checks become part of standard PR validation.

Tradeoffs:
- More middleware complexity and small runtime overhead.
- Trivy and Bandit can produce false positives; thresholds are tuned to avoid blocking low-severity noise.
- Session rekeying introduces a one-time session rotation event per authenticated session.

## Implementation references

- `src/nbms_app/middleware_request_id.py`
- `src/nbms_app/logging_utils.py`
- `src/nbms_app/middleware_security.py`
- `src/config/settings/base.py`
- `src/config/settings/prod.py`
- `src/nbms_app/api_spa.py` (`api_system_health`)
- `frontend/src/app/pages/system-health-page.component.ts`
- `.github/workflows/ci.yml`
