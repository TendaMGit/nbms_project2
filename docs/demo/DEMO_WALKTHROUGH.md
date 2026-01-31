# Demo Walkthrough (15-20 minutes)

This walkthrough uses the deterministic demo seed to show the end-to-end reporting flow.

## 0) Seed and start the server
```
$env:DJANGO_SETTINGS_MODULE='config.settings.dev'
$env:ENABLE_GIS='false'
$env:USE_REDIS='0'
$env:PYTHONPATH="$PWD\src"
python manage.py demo_seed
python manage.py runserver
```

## 1) Login
- User: `demo_admin`
- Password: `demo1234`
- URL: `/account/login/`

## 2) Review dashboard + coverage panel
- Open: `/reporting/instances/<uuid>/review/`
- Confirm coverage panel shows:
  - One mapped + one unmapped target
  - One mapped + one unmapped indicator

## 3) Alignment coverage (details)
- Open: `/reporting/instances/<uuid>/alignment-coverage/`
- Confirm orphans list shows the unmapped target and indicator.

## 4) Resolve an orphan mapping
- Open: `/reporting/instances/<uuid>/alignment/orphans/national-targets/`
- Select the orphan target (DEMO-NT-2) and map to DEMO-T2.
- Return to coverage page and confirm orphan count drops.

## 5) Approvals + consent blockers
- Open approvals: `/reporting/instances/<uuid>/approvals/`
  - Approve the remaining target + indicator.
- Open consent: `/reporting/instances/<uuid>/consent/`
  - Grant consent for the IPLC-sensitive evidence.

## 6) Review pack + export
- Review pack v2: `/reporting/instances/<uuid>/review-pack-v2/`
- Export (ORT NR7 v2): `/exports/instances/<uuid>/ort-nr7-v2.json`

## 7) CLI verification
```
python manage.py demo_verify --resolve-blockers
```
Expected output:
- Export JSON written to `docs/demo/golden/demo_ort_nr7_v2.json`
- Review pack ordering written to `docs/demo/golden/review_pack_order.json`
- A stable SHA256 hash printed

## Reset (optional)
```
python manage.py demo_seed --reset --confirm-reset
```

