# GeoServer connection (PostGIS)

Prereqs:
- GeoServer running at `GEOSERVER_URL`
- PostGIS reachable from GeoServer

## Connect GeoServer to PostGIS

Option A: Use the bootstrap script (requires curl):

```
GEOSERVER_URL=http://localhost:8080/geoserver \
GEOSERVER_USER=admin \
GEOSERVER_PASSWORD=replace-me \
GEOSERVER_WORKSPACE=nbms \
GEOSERVER_DATASTORE=nbms_postgis \
POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
NBMS_DB_NAME=nbms_project_db2 \
NBMS_DB_USER=nbms_user \
NBMS_DB_PASSWORD=replace-me \
./scripts/geoserver_bootstrap.sh
```

Option B: Manual steps in the GeoServer UI:
1) Log in to GeoServer.
2) Create a workspace (e.g., `nbms`).
3) Add a PostGIS store under that workspace:
   - Host: `POSTGRES_HOST`
   - Port: `POSTGRES_PORT`
   - Database: `NBMS_DB_NAME`
   - User: `NBMS_DB_USER`
   - Password: `NBMS_DB_PASSWORD`
4) Publish layers from the new datastore.
