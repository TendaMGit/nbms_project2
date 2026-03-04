from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import connection

from nbms_app.models import DatasetRelease, Indicator, IndicatorDataPoint, IndicatorDataSeries, LifecycleStatus, SensitivityLevel
from nbms_app.services.analytics_schema import (
    INDICATOR_LATEST_VALUE_VIEW,
    INDICATOR_TIMESERIES_VIEW,
    analytics_view_names,
)


class Command(BaseCommand):
    help = "Print operational and analytics-schema health counts for Superset troubleshooting."

    def handle(self, *args, **options):
        self.stdout.write("Operational counts")
        self.stdout.write(f"- indicators: {Indicator.objects.count()}")
        self.stdout.write(f"- series: {IndicatorDataSeries.objects.count()}")
        self.stdout.write(f"- datapoints: {IndicatorDataPoint.objects.count()}")
        self.stdout.write(f"- dataset releases: {DatasetRelease.objects.count()}")
        self.stdout.write(
            "- approved/published releases: "
            f"{DatasetRelease.objects.filter(status=LifecycleStatus.PUBLISHED, sensitivity=SensitivityLevel.PUBLIC, export_approved=True).count()}"
        )

        self.stdout.write("")
        self.stdout.write("Analytics view counts")
        with connection.cursor() as cursor:
            for view_name in analytics_view_names():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
                    count = cursor.fetchone()[0]
                    self.stdout.write(f"- {view_name}: {count}")
                except Exception as exc:  # pragma: no cover - diagnostic output
                    self.stdout.write(f"- {view_name}: ERROR {exc}")

            self.stdout.write("")
            self.stdout.write(f"Sample rows from {INDICATOR_TIMESERIES_VIEW}")
            self._print_samples(cursor, INDICATOR_TIMESERIES_VIEW)

            self.stdout.write("")
            self.stdout.write(f"Sample rows from {INDICATOR_LATEST_VALUE_VIEW}")
            self._print_samples(cursor, INDICATOR_LATEST_VALUE_VIEW)

    def _print_samples(self, cursor, view_name: str) -> None:
        try:
            cursor.execute(
                f"SELECT row_to_json(sample) FROM (SELECT * FROM {view_name} ORDER BY 1 LIMIT 5) sample"
            )
            rows = [row[0] for row in cursor.fetchall()]
        except Exception as exc:  # pragma: no cover - diagnostic output
            self.stdout.write(f"- ERROR {exc}")
            return
        if not rows:
            self.stdout.write("- no rows")
            return
        for row in rows:
            self.stdout.write(f"- {row}")
