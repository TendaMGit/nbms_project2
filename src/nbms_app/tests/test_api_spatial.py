import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
)


pytestmark = pytest.mark.django_db


def _polygon(coords):
    return {"type": "Polygon", "coordinates": [coords]}


def test_spatial_layers_and_geojson_features_are_exposed(client):
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    target = NationalTarget.objects.create(
        code="T-A",
        title="Target A",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-SPATIAL",
        title="Spatial indicator",
        national_target=target,
        organisation=org,
        indicator_type=NationalIndicatorType.OTHER,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    layer = SpatialLayer.objects.create(
        name="Demo layer",
        slug="demo-layer",
        source_type=SpatialLayerSourceType.INDICATOR,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        indicator=indicator,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="F1",
        name="Feature 1",
        province_code="WC",
        year=2022,
        indicator=indicator,
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
        properties_json={"status": "ok"},
    )

    list_response = client.get(reverse("api_spatial_layers"))
    assert list_response.status_code == 200
    layers = list_response.json()["layers"]
    assert layers[0]["slug"] == "demo-layer"

    feature_response = client.get(reverse("api_spatial_layer_features", args=["demo-layer"]))
    assert feature_response.status_code == 200
    payload = feature_response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    assert payload["features"][0]["geometry"]["type"] == "Polygon"


def test_spatial_bbox_filter_is_applied(client):
    layer = SpatialLayer.objects.create(
        name="BBox layer",
        slug="bbox-layer",
        source_type=SpatialLayerSourceType.STATIC,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="IN",
        name="Inside",
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="OUT",
        name="Outside",
        geometry_json=_polygon([[28.0, -24.0], [29.0, -24.0], [29.0, -23.0], [28.0, -23.0], [28.0, -24.0]]),
    )

    response = client.get(
        reverse("api_spatial_layer_features", args=["bbox-layer"]),
        {"bbox": "17.5,-34.5,20.0,-32.5"},
    )
    assert response.status_code == 200
    payload = response.json()
    keys = [item["properties"]["feature_key"] for item in payload["features"]]
    assert keys == ["IN"]


def test_spatial_abac_hides_internal_layer_from_anonymous(client):
    org = Organisation.objects.create(name="Org Internal", org_code="ORG-INTERNAL")
    layer = SpatialLayer.objects.create(
        name="Internal layer",
        slug="internal-layer",
        source_type=SpatialLayerSourceType.STATIC,
        sensitivity=SensitivityLevel.INTERNAL,
        is_public=True,
        organisation=org,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="INTERNAL-1",
        name="Internal Feature",
        province_code="WC",
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
    )

    list_response = client.get(reverse("api_spatial_layers"))
    assert list_response.status_code == 200
    slugs = [item["slug"] for item in list_response.json()["layers"]]
    assert "internal-layer" not in slugs

    feature_response = client.get(reverse("api_spatial_layer_features", args=["internal-layer"]))
    assert feature_response.status_code == 404


def test_spatial_abac_allows_internal_layer_for_same_org_user(client):
    org = Organisation.objects.create(name="Org Internal 2", org_code="ORG-INTERNAL-2")
    layer = SpatialLayer.objects.create(
        name="Internal layer 2",
        slug="internal-layer-2",
        source_type=SpatialLayerSourceType.STATIC,
        sensitivity=SensitivityLevel.INTERNAL,
        is_public=True,
        organisation=org,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="INTERNAL-2",
        name="Internal Feature 2",
        province_code="WC",
        geometry_json=_polygon([[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]),
    )

    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="spatial_org_user",
        password="testpass123",
        organisation=org,
    )
    assert client.login(username=user.username, password="testpass123")

    list_response = client.get(reverse("api_spatial_layers"))
    assert list_response.status_code == 200
    slugs = [item["slug"] for item in list_response.json()["layers"]]
    assert "internal-layer-2" in slugs

    feature_response = client.get(reverse("api_spatial_layer_features", args=["internal-layer-2"]))
    assert feature_response.status_code == 200
    payload = feature_response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
