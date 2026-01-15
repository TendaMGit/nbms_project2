from datetime import date

from django.test import TestCase
from django.urls import reverse

from nbms_app.models import ExportPackage, ExportStatus, Organisation, ReportingCycle, ReportingInstance, User


class ExportReadinessPanelTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.user = User.objects.create_user(
            username="creator",
            password="pass1234",
            organisation=self.org,
        )
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-EXP",
            title="Cycle Export",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

    def test_export_readiness_blocker_message(self):
        package = ExportPackage.objects.create(
            title="Export A",
            organisation=self.org,
            created_by=self.user,
            reporting_instance=self.instance,
            status=ExportStatus.DRAFT,
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:export_package_detail", args=[package.uuid]))
        self.assertContains(resp, "Package Eligibility")
        self.assertContains(resp, "approved before release")

    def test_export_readiness_ok_when_approved(self):
        package = ExportPackage.objects.create(
            title="Export B",
            organisation=self.org,
            created_by=self.user,
            reporting_instance=self.instance,
            status=ExportStatus.APPROVED,
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:export_package_detail", args=[package.uuid]))
        self.assertContains(resp, "Package Eligibility")
