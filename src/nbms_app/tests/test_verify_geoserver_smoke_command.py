import pytest
from django.core.management import call_command

from nbms_app.models import SensitivityLevel, SpatialLayer, SpatialLayerSourceType


pytestmark = pytest.mark.django_db


def test_verify_geoserver_smoke_command(monkeypatch):
    layer = SpatialLayer.objects.create(
        layer_code="TEST_GS_SMOKE",
        title="GeoServer smoke",
        name="GeoServer smoke",
        slug="test-gs-smoke",
        source_type=SpatialLayerSourceType.NBMS_TABLE,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
        publish_to_geoserver=True,
        geoserver_layer_name="nbms_gs_test_gs_smoke",
    )
    assert layer.id

    monkeypatch.setenv("GEOSERVER_PASSWORD", "dummy")
    monkeypatch.setenv("GEOSERVER_WORKSPACE", "nbms")

    def fake_request(url, headers, timeout=30):  # noqa: ARG001
        if "version.xml" in url:
            return 200, b"<about><resource name='GeoServer'/></about>", "application/xml"
        if "GetCapabilities" in url:
            xml = b"<WMS_Capabilities><Layer><Name>nbms:nbms_gs_test_gs_smoke</Name></Layer></WMS_Capabilities>"
            return 200, xml, "application/xml"
        if "GetMap" in url:
            return 200, b"\x89PNG\r\n\x1a\n", "image/png"
        raise AssertionError(f"Unexpected URL in smoke test: {url}")

    monkeypatch.setattr("nbms_app.management.commands.verify_geoserver_smoke._request", fake_request)
    call_command("verify_geoserver_smoke")
