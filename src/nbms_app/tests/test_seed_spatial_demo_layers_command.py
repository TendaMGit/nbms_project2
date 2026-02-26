import pytest
from django.core.management import call_command

from nbms_app.models import SpatialFeature, SpatialLayer


pytestmark = pytest.mark.django_db


def test_seed_spatial_demo_layers_is_idempotent():
    call_command("seed_spatial_demo_layers")
    call_command("seed_spatial_demo_layers")

    assert SpatialLayer.objects.filter(slug="sa-provinces").exists()
    assert SpatialLayer.objects.filter(slug="protected-areas-demo").exists()
    assert SpatialLayer.objects.filter(slug="ecosystem-threat-status-demo").exists()
    assert SpatialFeature.objects.count() >= 7
