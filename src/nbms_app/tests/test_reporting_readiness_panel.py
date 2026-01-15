from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from nbms_app.models import (
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.instance_approvals import approve_for_instance


class ReportingReadinessPanelTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.staff = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=self.org,
            is_staff=True,
        )
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-READINESS",
            title="Cycle Readiness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

    @override_settings(EXPORT_REQUIRE_SECTIONS=True)
    def test_instance_readiness_panel_shows_blockers(self):
        ReportSectionTemplate.objects.create(
            code="section-i",
            title="Section I",
            ordering=1,
            schema_json={"required": True, "fields": [{"key": "summary"}]},
        )
        target = NationalTarget.objects.create(
            code="NT-IPLC",
            title="Target IPLC",
            organisation=self.org,
            created_by=self.staff,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )
        approve_for_instance(self.instance, target, self.staff, admin_override=True)

        self.client.force_login(self.staff)
        resp = self.client.get(reverse("nbms_app:reporting_instance_detail", args=[self.instance.uuid]))
        self.assertContains(resp, "Instance Readiness")
        self.assertContains(resp, "Missing required sections")
        self.assertContains(resp, "Missing consent for approved IPLC records")
