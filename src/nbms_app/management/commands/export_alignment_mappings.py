import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from nbms_app.models import IndicatorFrameworkIndicatorLink, NationalTargetFrameworkTargetLink


FIELDNAMES = [
    "mapping_type",
    "national_target_uuid",
    "national_target_code",
    "framework_code",
    "framework_target_code",
    "indicator_uuid",
    "indicator_code",
    "framework_indicator_code",
    "relation_type",
    "confidence",
    "notes",
    "source",
]


class Command(BaseCommand):
    help = "Export alignment mappings to a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("--out", required=True, help="Output CSV path.")

    def handle(self, *args, **options):
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        target_links = (
            NationalTargetFrameworkTargetLink.objects.select_related(
                "national_target",
                "framework_target",
                "framework_target__framework",
            )
            .order_by("national_target__code", "framework_target__code")
        )
        indicator_links = (
            IndicatorFrameworkIndicatorLink.objects.select_related(
                "indicator",
                "framework_indicator",
                "framework_indicator__framework",
            )
            .order_by("indicator__code", "framework_indicator__code")
        )

        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()

            for link in target_links:
                writer.writerow(
                    {
                        "mapping_type": "national_target_framework_target",
                        "national_target_uuid": str(link.national_target.uuid),
                        "national_target_code": link.national_target.code,
                        "framework_code": link.framework_target.framework.code,
                        "framework_target_code": link.framework_target.code,
                        "indicator_uuid": "",
                        "indicator_code": "",
                        "framework_indicator_code": "",
                        "relation_type": link.relation_type,
                        "confidence": link.confidence if link.confidence is not None else "",
                        "notes": link.notes,
                        "source": link.source,
                    }
                )

            for link in indicator_links:
                writer.writerow(
                    {
                        "mapping_type": "indicator_framework_indicator",
                        "national_target_uuid": "",
                        "national_target_code": "",
                        "framework_code": link.framework_indicator.framework.code,
                        "framework_target_code": "",
                        "indicator_uuid": str(link.indicator.uuid),
                        "indicator_code": link.indicator.code,
                        "framework_indicator_code": link.framework_indicator.code,
                        "relation_type": link.relation_type,
                        "confidence": link.confidence if link.confidence is not None else "",
                        "notes": link.notes,
                        "source": link.source,
                    }
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {target_links.count()} target link(s) and {indicator_links.count()} indicator link(s)."
            )
        )
