from datetime import date

from django.test import TestCase

from nbms_app.models import ReportingCycle, ReportingInstance, ReportingStatus


class ReportingModelTests(TestCase):
    def test_reporting_cycle_defaults(self):
        cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.assertFalse(cycle.is_active)

    def test_reporting_instance_defaults(self):
        cycle = ReportingCycle.objects.create(
            code="CYCLE-2",
            title="Cycle 2",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        instance = ReportingInstance.objects.create(cycle=cycle)
        self.assertEqual(instance.status, ReportingStatus.DRAFT)
        self.assertEqual(instance.version_label, "v1")
        self.assertIsNone(instance.frozen_at)
