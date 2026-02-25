# Warnings Register

Date: 2026-02-25
Owner: platform engineering

## Active warnings

1. Django URLField scheme transition warning (`FORMS_URLFIELD_ASSUME_HTTPS`)
- Source: pytest warning (`RemovedInDjango60Warning`).
- Current mitigation: `FORMS_URLFIELD_ASSUME_HTTPS=true` in settings.
- Follow-up: migrate URL form fields to explicit `assume_scheme` and remove transitional setting.
- Owner: backend platform
- Remove-by date: 2026-09-30

2. drf-spectacular schema warnings on APIView endpoints
- Source: `python manage.py check --deploy` emits `drf_spectacular.W001/W002`.
- Impact: schema generation quality only; runtime API unaffected.
- Follow-up:
  - add explicit serializers or `@extend_schema` to high-traffic API endpoints,
  - resolve operationId collisions and untyped path params.
- Owner: API platform
- Remove-by date: 2026-06-30

3. Angular CommonJS warning for Plotly
- Source: Angular build warning for `plotly.js-dist-min`.
- Current mitigation: `allowedCommonJsDependencies` configured in `angular.json`.
- Follow-up: evaluate an ESM-native chart stack to reduce lazy chunk size.
- Owner: frontend platform
- Remove-by date: 2026-06-30

## Verification commands

```bash
python manage.py check
pytest -q
npm --prefix frontend run build
```

If a warning is intentionally tolerated, add rationale and expiry to `docs/security/SECURITY_EXCEPTIONS.md`.
