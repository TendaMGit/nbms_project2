import pytest
from django.core.management import call_command
from django.db import connection

from nbms_app.management.commands.seed_demo_indicator_outputs import (
    DEMO_INDICATOR_CODES,
    DEMO_RELEASE_VERSION,
)
from nbms_app.models import Indicator, IndicatorDataPoint, LifecycleStatus, SensitivityLevel
from nbms_app.services.analytics_schema import (
    BOUNDARY_PROVINCE_GEOJSON_VIEW,
    DIM_INDICATOR_VIEW,
    FACT_INDICATOR_OBSERVATION_VIEW,
    FACT_TARGET_ROLLUP_VIEW,
    INDICATOR_LATEST_VALUE_VIEW,
)


pytestmark = pytest.mark.django_db


def test_seed_demo_indicator_outputs_is_idempotent_and_marks_demo_slice_exportable():
    call_command("seed_demo_indicator_outputs")
    first_count = IndicatorDataPoint.objects.filter(
        series__indicator__code__in=DEMO_INDICATOR_CODES,
        dataset_release__version=DEMO_RELEASE_VERSION,
    ).count()

    call_command("seed_demo_indicator_outputs")
    second_count = IndicatorDataPoint.objects.filter(
        series__indicator__code__in=DEMO_INDICATOR_CODES,
        dataset_release__version=DEMO_RELEASE_VERSION,
    ).count()

    assert first_count == 160
    assert second_count == 160
    assert (
        Indicator.objects.filter(
            code__in=DEMO_INDICATOR_CODES,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
            export_approved=True,
        ).count()
        == len(DEMO_INDICATOR_CODES)
    )


def test_analytics_schema_has_rows_after_demo_seed():
    call_command("seed_demo_indicator_outputs")
    call_command("create_analytics_views")

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {FACT_INDICATOR_OBSERVATION_VIEW}")
        assert cursor.fetchone()[0] > 0

        cursor.execute(f"SELECT COUNT(*) FROM {DIM_INDICATOR_VIEW}")
        assert cursor.fetchone()[0] >= len(DEMO_INDICATOR_CODES)

        cursor.execute(
            f"SELECT COUNT(*) FROM {INDICATOR_LATEST_VALUE_VIEW} WHERE indicator_code = %s",
            ["NBMS-GBF-PA-COVERAGE"],
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute(f"SELECT COUNT(*) FROM {BOUNDARY_PROVINCE_GEOJSON_VIEW}")
        assert cursor.fetchone()[0] >= 9

        cursor.execute(f"SELECT COUNT(*) FROM {FACT_TARGET_ROLLUP_VIEW}")
        assert cursor.fetchone()[0] >= 1
