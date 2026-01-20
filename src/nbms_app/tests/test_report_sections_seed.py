from django.core.management import call_command
from django.test import TestCase

from nbms_app.models import ReportSectionTemplate


class ReportSectionSeedTests(TestCase):
    def test_seed_report_templates(self):
        self.assertEqual(ReportSectionTemplate.objects.count(), 0)
        call_command("seed_report_templates")
        self.assertEqual(ReportSectionTemplate.objects.count(), 6)
        call_command("seed_report_templates")
        self.assertEqual(ReportSectionTemplate.objects.count(), 6)
