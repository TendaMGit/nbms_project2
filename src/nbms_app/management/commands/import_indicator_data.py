import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import (
    DatasetRelease,
    Framework,
    FrameworkIndicator,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorValueType,
)


def _parse_json(value, field, row_number):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CommandError(f"Row {row_number}: invalid JSON in {field}: {exc}") from exc


def _parse_decimal(value, field, row_number):
    if value in (None, ""):
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise CommandError(f"Row {row_number}: invalid decimal in {field}: {value}") from exc


def _parse_bool(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    return None


class Command(BaseCommand):
    help = "Import indicator data series and points from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", required=True, help="Input CSV path.")
        parser.add_argument("--mode", default="upsert", choices=["upsert"], help="Import mode (default: upsert).")

    def handle(self, *args, **options):
        in_path = Path(options["in_path"])
        if not in_path.exists():
            raise CommandError(f"Input CSV not found: {in_path}")

        created_series = 0
        updated_series = 0
        created_points = 0
        updated_points = 0
        errors = []

        with in_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row_number, row in enumerate(reader, start=2):
                try:
                    framework_code = (row.get("framework_code") or "").strip()
                    framework_indicator_code = (row.get("framework_indicator_code") or "").strip()
                    indicator_uuid = (row.get("indicator_uuid") or "").strip()
                    indicator_code = (row.get("indicator_code") or "").strip()

                    framework_indicator = None
                    indicator = None

                    if framework_indicator_code:
                        if not framework_code:
                            raise CommandError(
                                f"Row {row_number}: framework_code is required when framework_indicator_code is set."
                            )
                        framework = Framework.objects.filter(code=framework_code).first()
                        if not framework:
                            raise CommandError(f"Row {row_number}: framework not found: {framework_code}")
                        framework_indicator = FrameworkIndicator.objects.filter(
                            framework=framework,
                            code=framework_indicator_code,
                        ).first()
                        if not framework_indicator:
                            raise CommandError(
                                f"Row {row_number}: framework indicator not found: {framework_code}:{framework_indicator_code}"
                            )
                    elif indicator_uuid:
                        indicator = Indicator.objects.filter(uuid=indicator_uuid).first()
                        if not indicator:
                            raise CommandError(f"Row {row_number}: indicator UUID not found: {indicator_uuid}")
                    elif indicator_code:
                        indicator = Indicator.objects.filter(code=indicator_code).first()
                        if not indicator:
                            raise CommandError(f"Row {row_number}: indicator code not found: {indicator_code}")
                    else:
                        raise CommandError(
                            f"Row {row_number}: indicator_uuid/indicator_code or framework_indicator_code required."
                        )

                    series_lookup = {}
                    if framework_indicator:
                        series_lookup["framework_indicator"] = framework_indicator
                    if indicator:
                        series_lookup["indicator"] = indicator

                    if not series_lookup:
                        raise CommandError(f"Row {row_number}: unable to resolve series identity.")

                    value_type_raw = (row.get("value_type") or "").strip()
                    value_type = value_type_raw or IndicatorValueType.NUMERIC
                    disaggregation_schema = _parse_json(
                        row.get("disaggregation_schema_json") or "",
                        "disaggregation_schema_json",
                        row_number,
                    )

                    series_defaults = {
                        "title": (row.get("series_title") or "").strip(),
                        "unit": (row.get("unit") or "").strip(),
                        "value_type": value_type,
                        "methodology": (row.get("methodology") or "").strip(),
                        "disaggregation_schema": disaggregation_schema or {},
                        "source_notes": (row.get("source_notes") or "").strip(),
                    }

                    series, created = IndicatorDataSeries.objects.get_or_create(
                        **series_lookup,
                        defaults=series_defaults,
                    )
                    if created:
                        created_series += 1
                    else:
                        updated_fields = []
                        for field, value in series_defaults.items():
                            if field == "value_type":
                                continue
                            if value:
                                setattr(series, field, value)
                                updated_fields.append(field)
                        if value_type_raw:
                            series.value_type = value_type
                            updated_fields.append("value_type")
                        status = (row.get("status") or "").strip()
                        if status:
                            series.status = status
                            updated_fields.append("status")
                        sensitivity = (row.get("sensitivity") or "").strip()
                        if sensitivity:
                            series.sensitivity = sensitivity
                            updated_fields.append("sensitivity")
                        export_approved = _parse_bool(row.get("export_approved"))
                        if export_approved is not None:
                            series.export_approved = export_approved
                            updated_fields.append("export_approved")
                        if updated_fields:
                            series.save(update_fields=updated_fields)
                            updated_series += 1

                    year = row.get("year")
                    if not year:
                        raise CommandError(f"Row {row_number}: year is required for data points.")
                    year = int(year)

                    value_numeric = _parse_decimal(row.get("value_numeric"), "value_numeric", row_number)
                    value_text = (row.get("value_text") or "").strip() or None
                    if value_numeric is None and value_text is None:
                        raise CommandError(f"Row {row_number}: value_numeric or value_text is required.")

                    disaggregation = _parse_json(
                        row.get("disaggregation_json") or "",
                        "disaggregation_json",
                        row_number,
                    )
                    dataset_release_uuid = (row.get("dataset_release_uuid") or "").strip()
                    dataset_release = None
                    if dataset_release_uuid:
                        dataset_release = DatasetRelease.objects.filter(uuid=dataset_release_uuid).first()
                        if not dataset_release:
                            raise CommandError(
                                f"Row {row_number}: dataset_release UUID not found: {dataset_release_uuid}"
                            )

                    point_defaults = {
                        "value_numeric": value_numeric,
                        "value_text": value_text,
                        "disaggregation": disaggregation or {},
                        "source_url": (row.get("source_url") or "").strip(),
                        "footnote": (row.get("footnote") or "").strip(),
                    }

                    point, point_created = IndicatorDataPoint.objects.update_or_create(
                        series=series,
                        year=year,
                        dataset_release=dataset_release,
                        disaggregation=disaggregation or {},
                        defaults=point_defaults,
                    )
                    if point_created:
                        created_points += 1
                    else:
                        updated_points += 1

                except CommandError as exc:
                    errors.append(str(exc))

        if errors:
            raise CommandError("Import failed:\n" + "\n".join(errors))

        self.stdout.write(
            self.style.SUCCESS(
                "Imported indicator data: "
                f"{created_series} series created, {updated_series} series updated, "
                f"{created_points} points created, {updated_points} points updated."
            )
        )
