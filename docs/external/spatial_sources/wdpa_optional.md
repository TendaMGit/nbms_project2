# WDPA Optional Integration (token-gated)

- Reference page: `https://www.protectedplanet.net/en/legal`
- Source class in NBMS: `WDPA_OPTIONAL`
- Default state: disabled (`enabled_by_default=false`)
- Token requirement: `WDPA_API_TOKEN` environment variable
- Auto-download behavior: OFF by default

NBMS policy in this increment:
- WDPA is not auto-downloaded without explicit opt-in.
- If token or format configuration is missing, sync returns a blocked status.
- Attribution/licensing metadata is retained on the `SpatialSource` record.
