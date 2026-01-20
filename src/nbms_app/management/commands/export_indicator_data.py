import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from nbms_app.models import IndicatorDataPoint


FIELDNAMES = [
    "series_uuid",
    "framework_code",
    "framework_indicator_code",
    "indicator_uuid",
    "indicator_code",
    "series_title",
    "unit",
    "value_type",
    "methodology",
    "disaggregation_schema_json",
    "source_notes",
    "status",
    "sensitivity",
    "export_approved",
    "year",
    "value_numeric",
    "value_text",
    "disaggregation_json",
    "dataset_release_uuid",
    "source_url",
    "footnote",
]


class Command(BaseCommand):
    help = "Export indicator data series and points to a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("--out", required=True, help="Output CSV path.")

    def handle(self, *args, **options):
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        points = (
            IndicatorDataPoint.objects.select_related(
                "series",
                "series__framework_indicator",
                "series__framework_indicator__framework",
                "series__indicator",
                "dataset_release",
            )
            .order_by("series__id", "year", "id")
        )

        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()

            for point in points:
                series = point.series
                framework = series.framework_indicator.framework if series.framework_indicator else None
                writer.writerow(
                    {
                        "series_uuid": str(series.uuid),
                        "framework_code": framework.code if framework else "",
                        "framework_indicator_code": series.framework_indicator.code if series.framework_indicator else "",
                        "indicator_uuid": str(series.indicator.uuid) if series.indicator else "",
                        "indicator_code": series.indicator.code if series.indicator else "",
                        "series_title": series.title,
                        "unit": series.unit,
                        "value_type": series.value_type,
                        "methodology": series.methodology,
                        "disaggregation_schema_json": json.dumps(series.disaggregation_schema or {}, sort_keys=True),
                        "source_notes": series.source_notes,
                        "status": series.status,
                        "sensitivity": series.sensitivity,
                        "export_approved": str(series.export_approved),
                        "year": point.year,
                        "value_numeric": str(point.value_numeric) if point.value_numeric is not None else "",
                        "value_text": point.value_text or "",
                        "disaggregation_json": json.dumps(point.disaggregation or {}, sort_keys=True),
                        "dataset_release_uuid": str(point.dataset_release.uuid) if point.dataset_release else "",
                        "source_url": point.source_url,
                        "footnote": point.footnote,
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Exported {points.count()} indicator data point(s)."))
