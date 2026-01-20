import json
from importlib import resources

from django.core.management.base import BaseCommand

from nbms_app.models import (
    BinaryIndicatorQuestion,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
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
        indicators_created = 0
        questions_created = 0
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

            _, was_created = BinaryIndicatorQuestion.objects.update_or_create(
                framework_indicator=indicator,
                group_key=record.get("group_key", ""),
                question_key=record.get("question_key", ""),
                defaults={
                    "section": record.get("section", ""),
                    "number": record.get("number", ""),
                    "question_type": record.get("question_type") or "option",
                    "question_text": record.get("question_text_key", ""),
                    "multiple": bool(record.get("multiple")),
                    "mandatory": bool(record.get("mandatory")),
                    "options": record.get("options", []),
                    "sort_order": record.get("sort_order", 0),
                },
            )
            if was_created:
                questions_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Ensured {len(records)} binary questions ({questions_created} created) "
                f"across {FrameworkIndicator.objects.filter(framework=framework, indicator_type=FrameworkIndicatorType.BINARY).count()} "
                f"binary indicators ({indicators_created} created)."
            )
        )
