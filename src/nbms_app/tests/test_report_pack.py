from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    ApprovalDecision,
    Indicator,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.views import build_report_pack_context


class ReportPackTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")
        self.staff_user = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=self.org_a,
            is_staff=True,
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org_a,
        )
        self.cycle = ReportingCycle.objects.create(
            code="C1",
            title="Cycle 1",
            start_date=date.today(),
            end_date=date.today(),
            due_date=date.today(),
            is_active=True,
        )
        self.instance = ReportingInstance.objects.create(
            cycle=self.cycle,
            version_label="v1",
        )
        self.template = ReportSectionTemplate.objects.create(
            code="section-i",
            title="Section I",
            ordering=1,
            schema_json={"fields": [{"key": "summary", "label": "Summary"}], "required": True},
            is_active=True,
        )
        ReportSectionResponse.objects.create(
            reporting_instance=self.instance,
            template=self.template,
            response_json={"summary": "Test summary"},
            updated_by=self.staff_user,
        )

    def test_staff_can_view_report_pack(self):
        self.client.force_login(self.staff_user)
        url = reverse("nbms_app:reporting_instance_report_pack", args=[self.instance.uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manager Report Pack")
        self.assertContains(response, "Readiness score")
        self.assertContains(response, "Section I")

    def test_non_staff_forbidden(self):
        self.client.force_login(self.viewer)
        url = reverse("nbms_app:reporting_instance_report_pack", args=[self.instance.uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_report_pack_applies_abac_filtering(self):
        target_a = NationalTarget.objects.create(
            code="TA",
            title="Target A",
            organisation=self.org_a,
            created_by=self.viewer,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        target_b = NationalTarget.objects.create(
            code="TB",
            title="Target B",
            organisation=self.org_b,
            created_by=self.staff_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.RESTRICTED,
        )
        indicator_visible = Indicator.objects.create(
            code="I1",
            title="Visible Indicator",
            national_target=target_a,
            organisation=self.org_a,
            created_by=self.viewer,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        indicator_hidden = Indicator.objects.create(
            code="I2",
            title="Hidden Indicator",
            national_target=target_b,
            organisation=self.org_b,
            created_by=self.staff_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.RESTRICTED,
        )
        content_type = ContentType.objects.get_for_model(Indicator)
        for indicator in (indicator_visible, indicator_hidden):
            InstanceExportApproval.objects.create(
                reporting_instance=self.instance,
                content_type=content_type,
                object_uuid=indicator.uuid,
                decision=ApprovalDecision.APPROVED,
                approval_scope="export",
            )

        context = build_report_pack_context(self.instance, self.viewer)
        approved_codes = {item.code for item in context["approved_indicators"]}
        self.assertIn(indicator_visible.code, approved_codes)
        self.assertNotIn(indicator_hidden.code, approved_codes)
