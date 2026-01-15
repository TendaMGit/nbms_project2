from datetime import date

from django.db import IntegrityError
from django.test import TestCase

from nbms_app.models import ReportSectionResponse, ReportSectionTemplate, ReportingCycle, ReportingInstance


class ReportSectionModelTests(TestCase):
    def setUp(self):
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-9",
            title="Cycle 9",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle)

    def test_section_template_create(self):
        template = ReportSectionTemplate.objects.create(code="section-i", title="Section I", ordering=1)
        self.assertEqual(template.code, "section-i")

    def test_section_response_unique_per_instance(self):
        template = ReportSectionTemplate.objects.create(code="section-ii", title="Section II", ordering=2)
        ReportSectionResponse.objects.create(reporting_instance=self.instance, template=template, response_json={"a": "b"})
        with self.assertRaises(IntegrityError):
            ReportSectionResponse.objects.create(reporting_instance=self.instance, template=template, response_json={"a": "c"})
