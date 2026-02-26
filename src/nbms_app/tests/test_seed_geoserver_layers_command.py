import pytest
from django.core.management import call_command

from nbms_app.management.commands.seed_geoserver_layers import GeoServerClient
from nbms_app.models import SensitivityLevel, SpatialFeature, SpatialLayer, SpatialLayerSourceType


pytestmark = pytest.mark.django_db


def _polygon(coords):
    return {"type": "Polygon", "coordinates": [coords]}


def test_seed_geoserver_layers_command(monkeypatch):
    layer = SpatialLayer.objects.create(
        layer_code="TEST_GEOSERVER_LAYER",
        title="GeoServer layer",
        name="GeoServer layer",
        slug="test-geoserver-layer",
        source_type=SpatialLayerSourceType.NBMS_TABLE,
        data_ref="nbms_app_spatialfeature",
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_id="F1",
        feature_key="F1",
        name="Feature One",
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
        properties={"name": "Feature One"},
        properties_json={"name": "Feature One"},
    )

    called = {"published": 0}

    monkeypatch.setenv("GEOSERVER_PASSWORD", "dummy")
    monkeypatch.setattr(GeoServerClient, "ensure_workspace", lambda self, workspace: None)
    monkeypatch.setattr(
        GeoServerClient,
        "ensure_postgis_store",
        lambda self, **kwargs: None,
    )
    monkeypatch.setattr(
        GeoServerClient,
        "publish_feature_type",
        lambda self, **kwargs: called.__setitem__("published", called["published"] + 1),
    )

    call_command("seed_geoserver_layers", "--layer-code", "TEST_GEOSERVER_LAYER")
    assert called["published"] >= 1
