#!/usr/bin/env bash
set -euo pipefail

GEOSERVER_URL="${GEOSERVER_URL:-http://localhost:8080/geoserver}"
GEOSERVER_USER="${GEOSERVER_USER:-admin}"
GEOSERVER_PASSWORD="${GEOSERVER_PASSWORD:?GEOSERVER_PASSWORD is required}"
GEOSERVER_WORKSPACE="${GEOSERVER_WORKSPACE:-nbms}"
GEOSERVER_DATASTORE="${GEOSERVER_DATASTORE:-nbms_postgis}"

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${NBMS_DB_NAME:-nbms_project_db2}"
DB_USER="${NBMS_DB_USER:-nbms_user}"
DB_PASSWORD="${NBMS_DB_PASSWORD:?NBMS_DB_PASSWORD is required}"

AUTH="$GEOSERVER_USER:$GEOSERVER_PASSWORD"

if ! curl -sf -u "$AUTH" "$GEOSERVER_URL/rest/workspaces/$GEOSERVER_WORKSPACE" > /dev/null; then
  curl -sf -u "$AUTH" -H "Content-Type: text/xml" \
    -d "<workspace><name>$GEOSERVER_WORKSPACE</name></workspace>" \
    "$GEOSERVER_URL/rest/workspaces" > /dev/null
fi

if ! curl -sf -u "$AUTH" "$GEOSERVER_URL/rest/workspaces/$GEOSERVER_WORKSPACE/datastores/$GEOSERVER_DATASTORE" > /dev/null; then
  cat <<EOF | curl -sf -u "$AUTH" -H "Content-Type: text/xml" -d @- \
    "$GEOSERVER_URL/rest/workspaces/$GEOSERVER_WORKSPACE/datastores" > /dev/null
<datastore>
  <name>$GEOSERVER_DATASTORE</name>
  <connectionParameters>
    <host>$DB_HOST</host>
    <port>$DB_PORT</port>
    <database>$DB_NAME</database>
    <user>$DB_USER</user>
    <passwd>$DB_PASSWORD</passwd>
    <dbtype>postgis</dbtype>
  </connectionParameters>
</datastore>
EOF
fi
