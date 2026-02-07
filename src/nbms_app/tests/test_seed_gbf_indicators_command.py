import pytest
from django.core.management import call_command

from nbms_app.models import Indicator, IndicatorMethodProfile, IndicatorMethodRun, IndicatorMethodType


pytestmark = pytest.mark.django_db


def test_seed_gbf_indicators_populates_catalog_and_methods():
    call_command("seed_gbf_indicators")

    assert Indicator.objects.filter(code__startswith="GBF-H-").count() >= 13
    assert Indicator.objects.filter(code__startswith="GBF-BI-").count() >= 22
    assert IndicatorMethodProfile.objects.count() >= 35
    assert IndicatorMethodRun.objects.count() >= 3

    seeded_types = set(IndicatorMethodProfile.objects.values_list("method_type", flat=True))
    expected_types = {
        IndicatorMethodType.MANUAL,
        IndicatorMethodType.CSV_IMPORT,
        IndicatorMethodType.API_CONNECTOR,
        IndicatorMethodType.SCRIPTED_PYTHON,
        IndicatorMethodType.SCRIPTED_R_CONTAINER,
        IndicatorMethodType.SPATIAL_OVERLAY,
        IndicatorMethodType.SEEA_ACCOUNTING,
        IndicatorMethodType.BINARY_QUESTIONNAIRE,
    }
    assert expected_types.issubset(seeded_types)
