import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from nbms_app.models import (
    AlignmentRelationType,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorFrameworkIndicatorLink,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
)


class Command(BaseCommand):
    help = "Import alignment mappings from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("--in", dest="in_path", required=True, help="Input CSV path.")
        parser.add_argument(
            "--mode",
            choices=["upsert", "insert"],
            default="upsert",
            help="Import mode (default: upsert).",
        )

    def handle(self, *args, **options):
        in_path = Path(options["in_path"])
        mode = options["mode"]
        if not in_path.exists():
            raise CommandError(f"Input file not found: {in_path}")

        errors = []
        created = 0
        updated = 0

        with in_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader, start=2):
                mapping_type = (row.get("mapping_type") or "").strip()
                if not mapping_type:
                    errors.append(f"Row {index}: missing mapping_type.")
                    continue
                try:
                    if mapping_type == "national_target_framework_target":
                        c, u = _import_target_mapping(row, mode)
                    elif mapping_type == "indicator_framework_indicator":
                        c, u = _import_indicator_mapping(row, mode)
                    else:
                        errors.append(f"Row {index}: invalid mapping_type '{mapping_type}'.")
                        continue
                except CommandError as exc:
                    errors.append(f"Row {index}: {exc}")
                    continue
                created += c
                updated += u

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError("Import failed due to validation errors.")

        self.stdout.write(self.style.SUCCESS(f"Import complete. Created: {created}, Updated: {updated}."))


def _import_target_mapping(row, mode):
    target = _resolve_target(row)
    framework = _resolve_framework(row)
    framework_target = _resolve_framework_target(row, framework)
    relation_type = _resolve_relation_type(row)
    confidence = _parse_confidence(row.get("confidence"))
    notes = (row.get("notes") or "").strip()
    source = (row.get("source") or "").strip()

    defaults = {
        "relation_type": relation_type,
        "confidence": confidence,
        "notes": notes,
        "source": source,
    }

    if mode == "insert":
        try:
            NationalTargetFrameworkTargetLink.objects.create(
                national_target=target,
                framework_target=framework_target,
                **defaults,
            )
        except IntegrityError as exc:
            raise CommandError(f"Mapping already exists for target {target.code}.") from exc
        return 1, 0

    link, created = NationalTargetFrameworkTargetLink.objects.update_or_create(
        national_target=target,
        framework_target=framework_target,
        defaults=defaults,
    )
    return (1, 0) if created else (0, 1)


def _import_indicator_mapping(row, mode):
    indicator = _resolve_indicator(row)
    framework = _resolve_framework(row)
    framework_indicator = _resolve_framework_indicator(row, framework)
    relation_type = _resolve_relation_type(row)
    confidence = _parse_confidence(row.get("confidence"))
    notes = (row.get("notes") or "").strip()
    source = (row.get("source") or "").strip()

    defaults = {
        "relation_type": relation_type,
        "confidence": confidence,
        "notes": notes,
        "source": source,
    }

    if mode == "insert":
        try:
            IndicatorFrameworkIndicatorLink.objects.create(
                indicator=indicator,
                framework_indicator=framework_indicator,
                **defaults,
            )
        except IntegrityError as exc:
            raise CommandError(f"Mapping already exists for indicator {indicator.code}.") from exc
        return 1, 0

    link, created = IndicatorFrameworkIndicatorLink.objects.update_or_create(
        indicator=indicator,
        framework_indicator=framework_indicator,
        defaults=defaults,
    )
    return (1, 0) if created else (0, 1)


def _resolve_framework(row):
    framework_code = (row.get("framework_code") or "").strip()
    if not framework_code:
        raise CommandError("Missing framework_code.")
    framework = Framework.objects.filter(code=framework_code).first()
    if not framework:
        raise CommandError(f"Framework not found for code '{framework_code}'.")
    return framework


def _resolve_framework_target(row, framework):
    target_code = (row.get("framework_target_code") or "").strip()
    if not target_code:
        raise CommandError("Missing framework_target_code.")
    framework_target = FrameworkTarget.objects.filter(framework=framework, code=target_code).first()
    if not framework_target:
        raise CommandError(
            f"FrameworkTarget not found for framework '{framework.code}' and code '{target_code}'."
        )
    return framework_target


def _resolve_framework_indicator(row, framework):
    indicator_code = (row.get("framework_indicator_code") or "").strip()
    if not indicator_code:
        raise CommandError("Missing framework_indicator_code.")
    framework_indicator = FrameworkIndicator.objects.filter(framework=framework, code=indicator_code).first()
    if not framework_indicator:
        raise CommandError(
            f"FrameworkIndicator not found for framework '{framework.code}' and code '{indicator_code}'."
        )
    return framework_indicator


def _resolve_target(row):
    target_uuid = (row.get("national_target_uuid") or "").strip()
    target_code = (row.get("national_target_code") or "").strip()
    target = None
    if target_uuid:
        target = NationalTarget.objects.filter(uuid=target_uuid).first()
    if not target and target_code:
        target = NationalTarget.objects.filter(code=target_code).first()
    if not target:
        raise CommandError("National target not found (provide national_target_uuid or national_target_code).")
    return target


def _resolve_indicator(row):
    indicator_uuid = (row.get("indicator_uuid") or "").strip()
    indicator_code = (row.get("indicator_code") or "").strip()
    indicator = None
    if indicator_uuid:
        indicator = Indicator.objects.filter(uuid=indicator_uuid).first()
    if not indicator and indicator_code:
        indicator = Indicator.objects.filter(code=indicator_code).first()
    if not indicator:
        raise CommandError("Indicator not found (provide indicator_uuid or indicator_code).")
    return indicator


def _resolve_relation_type(row):
    relation_type = (row.get("relation_type") or "").strip()
    if not relation_type:
        return AlignmentRelationType.CONTRIBUTES_TO
    valid = {choice.value for choice in AlignmentRelationType}
    if relation_type not in valid:
        raise CommandError(f"Invalid relation_type '{relation_type}'.")
    return relation_type


def _parse_confidence(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CommandError(f"Invalid confidence value '{value}'.") from exc
    if parsed < 0 or parsed > 100:
        raise CommandError("Confidence must be between 0 and 100.")
    return parsed
