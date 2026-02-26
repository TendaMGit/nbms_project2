from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand
from django.db import connection

from nbms_app.models import SpatialLayer, SpatialLayerSourceType
from nbms_app.spatial_fields import GIS_ENABLED


class GeoServerClient:
    def __init__(self, *, base_url, user, password):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        self.auth_header = f"Basic {token}"

    def request(self, method, path, payload=None, content_type="application/json", allow_404=False):
        body = None
        if payload is not None:
            if isinstance(payload, str):
                body = payload.encode("utf-8")
            else:
                body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{self.base_url}{path}", method=method, data=body)
        req.add_header("Authorization", self.auth_header)
        if body is not None:
            req.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.getcode(), response.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return exc.code, exc.read().decode("utf-8", errors="ignore")
            raise

    def ensure_workspace(self, workspace):
        code, _ = self.request("GET", f"/rest/workspaces/{workspace}.json", allow_404=True)
        if code == 404:
            self.request("POST", "/rest/workspaces", {"workspace": {"name": workspace}})

    def ensure_postgis_store(self, *, workspace, datastore, db_host, db_port, db_name, db_user, db_password):
        code, _ = self.request(
            "GET",
            f"/rest/workspaces/{workspace}/datastores/{datastore}.json",
            allow_404=True,
        )
        if code != 404:
            return
        payload = {
            "dataStore": {
                "name": datastore,
                "connectionParameters": {
                    "entry": [
                        {"@key": "dbtype", "$": "postgis"},
                        {"@key": "host", "$": db_host},
                        {"@key": "port", "$": str(db_port)},
                        {"@key": "database", "$": db_name},
                        {"@key": "user", "$": db_user},
                        {"@key": "passwd", "$": db_password},
                        {"@key": "schema", "$": "public"},
                    ]
                },
            }
        }
        self.request("POST", f"/rest/workspaces/{workspace}/datastores", payload)

    def publish_feature_type(self, *, workspace, datastore, table_name, title):
        payload = {"featureType": {"name": table_name, "nativeName": table_name, "title": title, "srs": "EPSG:4326"}}
        self.request(
            "POST",
            f"/rest/workspaces/{workspace}/datastores/{datastore}/featuretypes",
            payload,
        )


class Command(BaseCommand):
    help = "Publish NBMS spatial layers to GeoServer as WMS/WFS feature types."

    def add_arguments(self, parser):
        parser.add_argument("--layer-code", action="append", dest="layer_codes", default=[])

    def handle(self, *args, **options):
        geoserver_url = os.environ.get("GEOSERVER_URL", "http://localhost:8080/geoserver")
        geoserver_user = os.environ.get("GEOSERVER_USER", "admin")
        geoserver_password = os.environ.get("GEOSERVER_PASSWORD", "")
        workspace = os.environ.get("GEOSERVER_WORKSPACE", "nbms")
        datastore = os.environ.get("GEOSERVER_DATASTORE", "nbms_postgis")

        if not geoserver_password:
            self.stderr.write(self.style.ERROR("GEOSERVER_PASSWORD is required."))
            raise SystemExit(1)

        client = GeoServerClient(base_url=geoserver_url, user=geoserver_user, password=geoserver_password)
        client.ensure_workspace(workspace)

        db = connection.settings_dict
        client.ensure_postgis_store(
            workspace=workspace,
            datastore=datastore,
            db_host=db.get("HOST") or "postgis",
            db_port=db.get("PORT") or "5432",
            db_name=db.get("NAME"),
            db_user=db.get("USER"),
            db_password=db.get("PASSWORD") or "",
        )

        layers = SpatialLayer.objects.filter(is_active=True, publish_to_geoserver=True).order_by("layer_code")
        requested_codes = options.get("layer_codes") or []
        if requested_codes:
            layers = layers.filter(layer_code__in=requested_codes)

        published = 0
        skipped = 0
        for layer in layers:
            if layer.source_type not in {
                SpatialLayerSourceType.NBMS_TABLE,
                SpatialLayerSourceType.UPLOADED_FILE,
                SpatialLayerSourceType.STATIC,
                SpatialLayerSourceType.INDICATOR,
            }:
                skipped += 1
                continue

            view_name = (layer.geoserver_layer_name or "").strip() or f"nbms_gs_{layer.layer_code.lower()}"
            geom_expr = (
                "COALESCE(geom, ST_SetSRID(ST_GeomFromGeoJSON(geometry_json::text), 4326))"
                if GIS_ENABLED
                else "NULL::text"
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE OR REPLACE VIEW {view_name} AS
                    SELECT
                        id,
                        feature_id,
                        feature_key,
                        name,
                        province_code,
                        year,
                        COALESCE(properties, properties_json) AS properties,
                        {geom_expr} AS geom
                    FROM nbms_app_spatialfeature
                    WHERE layer_id = %s
                    """,
                    [layer.id],
                )

            try:
                client.publish_feature_type(
                    workspace=workspace,
                    datastore=datastore,
                    table_name=view_name,
                    title=layer.title or layer.name,
                )
                if layer.geoserver_layer_name != view_name:
                    layer.geoserver_layer_name = view_name
                    layer.save(update_fields=["geoserver_layer_name", "updated_at"])
            except urllib.error.HTTPError as exc:
                if exc.code not in {401, 403, 404, 409, 500}:
                    raise
            published += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"GeoServer publish complete. workspace={workspace}, datastore={datastore}, "
                f"published={published}, skipped={skipped}."
            )
        )
