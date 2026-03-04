import pytest
from django.core.management import call_command
from django.db import connection

from nbms_app.services.analytics_schema import (
    ANALYTICS_SCHEMA,
    FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW,
    INDICATOR_LATEST_VALUE_VIEW,
    INDICATOR_READINESS_SUMMARY_VIEW,
    INDICATOR_REGISTRY_VIEW,
    INDICATOR_SPATIAL_FEATURES_GEOJSON_VIEW,
    INDICATOR_TIMESERIES_VIEW,
    SPATIAL_UNITS_GEOJSON_VIEW,
)


pytestmark = pytest.mark.django_db


def test_create_analytics_views_exposes_published_indicator_outputs():
    call_command("seed_indicator_workflow_v2")
    call_command("create_analytics_views")

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {INDICATOR_REGISTRY_VIEW} WHERE indicator_code = %s", ["NBA_ECO_RLE_TERR"])
        assert cursor.fetchone()[0] == 1

        cursor.execute(f"SELECT COUNT(*) FROM {INDICATOR_TIMESERIES_VIEW} WHERE indicator_code = %s", ["NBA_ECO_RLE_TERR"])
        assert cursor.fetchone()[0] > 1

        cursor.execute(
            f"SELECT COUNT(*) FROM {INDICATOR_LATEST_VALUE_VIEW} WHERE indicator_code = %s",
            ["NBA_ECO_RLE_TERR"],
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute(
            f"SELECT COUNT(*) FROM {FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW} WHERE framework_code = %s AND indicator_code LIKE %s",
            ["GBF", "NBA_%"],
        )
        assert cursor.fetchone()[0] >= 1

        cursor.execute(
            f"SELECT readiness_state FROM {INDICATOR_READINESS_SUMMARY_VIEW} WHERE indicator_code = %s",
            ["NBA_ECO_RLE_TERR"],
        )
        readiness_state = cursor.fetchone()[0]
        assert readiness_state in {"ready", "partial"}

        cursor.execute(f"SELECT COUNT(*) FROM {SPATIAL_UNITS_GEOJSON_VIEW}")
        assert cursor.fetchone()[0] >= 1

        cursor.execute(f"SELECT COUNT(*) FROM {INDICATOR_SPATIAL_FEATURES_GEOJSON_VIEW}")
        assert cursor.fetchone()[0] >= 1


def test_ensure_superset_ro_is_idempotent_and_limited_to_analytics(monkeypatch):
    call_command("seed_indicator_workflow_v2")
    call_command("create_analytics_views")
    monkeypatch.setenv("SUPERSET_NBMS_RO_PASSWORD", "superset-ro-test-password")

    call_command("ensure_superset_ro")
    call_command("ensure_superset_ro")

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'superset_ro'")
        assert cursor.fetchone() == (1,)

        cursor.execute(
            "SELECT has_schema_privilege('superset_ro', %s, 'USAGE')",
            [ANALYTICS_SCHEMA],
        )
        assert cursor.fetchone()[0] is True

        cursor.execute(
            "SELECT has_table_privilege('superset_ro', 'public.nbms_app_indicator', 'SELECT')"
        )
        assert cursor.fetchone()[0] is False

        cursor.execute(
            "SELECT has_table_privilege('superset_ro', %s, 'SELECT')",
            [INDICATOR_REGISTRY_VIEW],
        )
        assert cursor.fetchone()[0] is True
