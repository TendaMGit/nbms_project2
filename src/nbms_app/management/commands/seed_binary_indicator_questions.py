import json
from importlib import resources

from django.core.management.base import BaseCommand

from nbms_app.models import (
    BinaryIndicatorGroup,
    BinaryIndicatorQuestion,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    LifecycleStatus,
    SensitivityLevel,
)


def _load_fixture():
    with resources.files("nbms_app.data").joinpath("ort_binary_indicator_questions.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


class Command(BaseCommand):
    help = "Seed binary indicator questions from the ORT reference fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--framework-code",
            default="GBF",
            help="Framework code to attach binary indicators to (default: GBF).",
        )
        parser.add_argument(
            "--framework-title",
            default="Global Biodiversity Framework",
            help="Framework title to use when creating the framework (default: Global Biodiversity Framework).",
        )

    def handle(self, *args, **options):
        framework_code = options["framework_code"]
        framework_title = options["framework_title"]

        framework, _ = Framework.objects.get_or_create(
            code=framework_code,
            defaults={
                "title": framework_title,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )

        records = _load_fixture()
        group_records = {}
        for record in records:
            group_key = record.get("group_key")
            if not group_key:
                continue
            entry = group_records.setdefault(
                group_key,
                {
                    "target_code": record.get("target", ""),
                    "binary_indicator": record.get("binary_indicator", ""),
                    "ordering": record.get("sort_order", 0),
                },
            )
            ordering = record.get("sort_order", 0)
            if ordering < entry["ordering"]:
                entry["ordering"] = ordering

        indicators_created = 0
        questions_created = 0
        groups_created = 0
        indicator_map = {}
        for record in records:
            indicator_code = record.get("binary_indicator")
            if not indicator_code:
                continue

            indicator, indicator_was_created = FrameworkIndicator.objects.update_or_create(
                framework=framework,
                code=indicator_code,
                defaults={
                    "title": indicator_code,
                    "indicator_type": FrameworkIndicatorType.BINARY,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                },
            )
            if indicator_was_created:
                indicators_created += 1
            indicator_map[indicator_code] = indicator

        group_map = {}
        for group_key, data in group_records.items():
            target_code = data.get("target_code") or ""
            target = FrameworkTarget.objects.filter(code=target_code).first() if target_code else None
            indicator_code = data.get("binary_indicator") or ""
            indicator = indicator_map.get(indicator_code)
            group, was_created = BinaryIndicatorGroup.objects.update_or_create(
                key=group_key,
                defaults={
                    "framework_target": target,
                    "framework_indicator": indicator,
                    "target_code": target_code,
                    "binary_indicator_code": indicator_code,
                    "ordering": data.get("ordering", 0),
                    "is_active": True,
                    "source_ref": "ort_binary_indicator_questions.json",
                },
            )
            if was_created:
                groups_created += 1
            group_map[group_key] = group

            group = group_map.get(record.get("group_key"))
            raw_type = (record.get("question_type") or "single").lower()
            if raw_type in {"option", "single"}:
                question_type = "single"
            elif raw_type in {"checkbox", "multiple"}:
                question_type = "multiple"
            elif raw_type in {"string", "text", "header"}:
                question_type = "text"
            else:
                question_type = "text"
            _, was_created = BinaryIndicatorQuestion.objects.update_or_create(
                framework_indicator=indicator,
                group_key=record.get("group_key", ""),
                question_key=record.get("question_key", ""),
                defaults={
                    "group": group,
                    "section": record.get("section", ""),
                    "number": record.get("number", ""),
                    "question_type": question_type,
                    "question_text": record.get("question_text_key", ""),
                    "multiple": bool(record.get("multiple")),
                    "mandatory": bool(record.get("mandatory")),
                    "options": record.get("options", []),
                    "sort_order": record.get("sort_order", 0),
                    "validations": record.get("validations", {}),
                    "is_active": True,
                },
            )
            if was_created:
                questions_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Ensured {len(records)} binary questions ({questions_created} created), "
                f"{len(group_records)} groups ({groups_created} created), "
                f"across {FrameworkIndicator.objects.filter(framework=framework, indicator_type=FrameworkIndicatorType.BINARY).count()} "
                f"binary indicators ({indicators_created} created)."
            )
        )
