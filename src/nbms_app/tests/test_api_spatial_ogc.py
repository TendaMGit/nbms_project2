import pytest
from django.urls import reverse

from nbms_app.models import (
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
)


pytestmark = pytest.mark.django_db


def _polygon(coords):
    return {"type": "Polygon", "coordinates": [coords]}


def test_ogc_collections_and_items_bbox(client):
    layer = SpatialLayer.objects.create(
        layer_code="TEST_OGC_LAYER",
        title="Test OGC Layer",
        name="Test OGC Layer",
        slug="test-ogc-layer",
        source_type=SpatialLayerSourceType.NBMS_TABLE,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_id="IN",
        feature_key="IN",
        name="Inside",
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
        properties={"status": "ok"},
        properties_json={"status": "ok"},
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_id="OUT",
        feature_key="OUT",
        name="Outside",
        geometry_json=_polygon([[28.0, -24.0], [29.0, -24.0], [29.0, -23.0], [28.0, -23.0], [28.0, -24.0]]),
        properties={"status": "ok"},
        properties_json={"status": "ok"},
    )

    collections = client.get(reverse("api_ogc_collections"))
    assert collections.status_code == 200
    ids = [row["id"] for row in collections.json()["collections"]]
    assert "TEST_OGC_LAYER" in ids

    items = client.get(
        reverse("api_ogc_collection_items", args=["TEST_OGC_LAYER"]),
        {"bbox": "17.5,-34.5,20.0,-32.5", "limit": 10},
    )
    assert items.status_code == 200
    payload = items.json()
    assert payload["type"] == "FeatureCollection"
    assert payload["numberReturned"] == 1
    assert payload["features"][0]["properties"]["feature_id"] == "IN"


def test_tilejson_and_mvt_endpoints(client):
    layer = SpatialLayer.objects.create(
        layer_code="TEST_TILE_LAYER",
        title="Test Tile Layer",
        name="Test Tile Layer",
        slug="test-tile-layer",
        source_type=SpatialLayerSourceType.NBMS_TABLE,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_id="A",
        feature_key="A",
        name="Feature A",
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
        properties={"status": "ok"},
        properties_json={"status": "ok"},
    )

    tilejson = client.get(reverse("api_tiles_tilejson", args=["TEST_TILE_LAYER"]))
    assert tilejson.status_code == 200
    assert tilejson.json()["tiles"]

    tile = client.get(reverse("api_tiles_mvt", args=["TEST_TILE_LAYER", 0, 0, 0]))
    assert tile.status_code == 200
    assert tile["Content-Type"] == "application/vnd.mapbox-vector-tile"
    assert "ETag" in tile
