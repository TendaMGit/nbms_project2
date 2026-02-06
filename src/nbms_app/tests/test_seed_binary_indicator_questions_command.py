import json
from importlib import resources

from django.core.management import call_command
from django.test import TestCase

from nbms_app.models import BinaryIndicatorQuestion


def _fixture_records():
    with resources.files("nbms_app.data").joinpath("ort_binary_indicator_questions.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


class SeedBinaryIndicatorQuestionsCommandTests(TestCase):
    def test_seeds_all_unique_questions_from_fixture(self):
        expected = {
            (
                record.get("binary_indicator", ""),
                record.get("group_key", ""),
                record.get("question_key", ""),
            )
            for record in _fixture_records()
            if record.get("binary_indicator")
        }

        call_command("seed_binary_indicator_questions")

        actual = set(
            BinaryIndicatorQuestion.objects.values_list(
                "framework_indicator__code",
                "group_key",
                "question_key",
            )
        )
        self.assertSetEqual(actual, expected)
        self.assertEqual(
            BinaryIndicatorQuestion.objects.filter(group__isnull=False).count(),
            len(expected),
        )
