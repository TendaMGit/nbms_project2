# ADR 0002: Angular Auth via Server Session + CSRF

- Status: Accepted
- Date: 2026-02-06

## Context
NBMS has strict governance requirements (RBAC/ABAC, consent gating, audit traceability, MFA compatibility). SPA adoption must not bypass existing server-side authorization controls.

## Decision
- Angular UI will use server-backed session authentication with CSRF protection.
- Authorization remains server-side in Django services/views/APIs; Angular is presentation and workflow orchestration only.
- Introduce `/api/auth/me` and `/api/auth/csrf` bootstrap endpoints, but avoid client-side trust for policy decisions.

## Consequences
- Preserves existing governance controls and two-factor login posture.
- Avoids introducing token lifecycle complexity for first Angular rollout.
- Requires careful CORS/CSRF configuration when frontend is served on a separate origin.
