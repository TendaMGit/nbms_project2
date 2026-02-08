import json
import shutil
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connection

from nbms_app.models import SpatialFeature, SpatialIngestionRun, SpatialLayer


pytestmark = pytest.mark.django_db


def _postgis_available() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Full_Version()")
            cursor.fetchone()
        return True
    except Exception:
        return False


@pytest.mark.skipif(shutil.which("ogr2ogr") is None, reason="ogr2ogr is required")
def test_ingest_spatial_layer_command_geojson(tmp_path):
    if not _postgis_available():
        pytest.skip("PostGIS functions are required for spatial ingestion tests.")

    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]],
                },
                "properties": {"name": "Feature A", "province_code": "WC", "year": 2023},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[20.0, -30.0], [21.0, -30.0], [21.0, -29.0], [20.0, -29.0], [20.0, -30.0]]],
                },
                "properties": {"name": "Feature B", "province_code": "EC", "year": 2022},
            },
        ],
    }
    source_file = Path(tmp_path) / "ingest.geojson"
    source_file.write_text(json.dumps(payload), encoding="utf-8")

    call_command(
        "ingest_spatial_layer",
        "--layer-code",
        "TEST_INGEST_LAYER",
        "--file",
        str(source_file),
        "--title",
        "Test Ingest Layer",
    )

    layer = SpatialLayer.objects.get(layer_code="TEST_INGEST_LAYER")
    assert SpatialFeature.objects.filter(layer=layer).count() >= 2
    run = SpatialIngestionRun.objects.filter(layer=layer).order_by("-created_at").first()
    assert run is not None
    assert run.status == "succeeded"
