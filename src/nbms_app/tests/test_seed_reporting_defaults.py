from django.core.management import call_command
from django.test import TestCase

from nbms_app.models import ReportSectionTemplate, ValidationRuleSet


class SeedReportingDefaultsTests(TestCase):
    def test_seed_reporting_defaults_creates_templates_and_rules(self):
        call_command("seed_reporting_defaults")

        self.assertGreater(ReportSectionTemplate.objects.count(), 0)
        self.assertTrue(ValidationRuleSet.objects.filter(code="7NR_DEFAULT").exists())
