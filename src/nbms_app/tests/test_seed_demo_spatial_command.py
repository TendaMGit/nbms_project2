import pytest
from django.core.management import call_command

from nbms_app.models import SpatialFeature, SpatialLayer, SpatialUnit, SpatialUnitType


pytestmark = pytest.mark.django_db


def test_seed_demo_spatial_is_idempotent():
    call_command("seed_demo_spatial")
    call_command("seed_demo_spatial")

    assert SpatialUnitType.objects.filter(code="PROVINCE").exists()
    assert SpatialUnit.objects.filter(unit_code__startswith="ZA-").count() >= 3
    assert SpatialLayer.objects.filter(layer_code__in=["ZA_PROVINCES", "ZA_PROTECTED_AREAS", "ZA_ECOSYSTEM_THREAT_STATUS"]).count() == 3
    assert SpatialFeature.objects.filter(layer__layer_code="ZA_PROVINCES").count() >= 3
