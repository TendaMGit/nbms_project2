from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nbms_app.models import Organisation, ReportSectionResponse, ReportSectionTemplate, ReportingCycle, ReportingInstance, User


class ReportSectionUiTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.staff = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=self.org,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="user",
            password="pass1234",
            organisation=self.org,
        )
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-3",
            title="Cycle 3",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle)
        self.template = ReportSectionTemplate.objects.create(
            code="section-i",
            title="Section I",
            ordering=1,
            schema_json={
                "fields": [
                    {"key": "summary", "label": "Summary", "required": True},
                ]
            },
        )

    def test_staff_can_view_sections(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("nbms_app:reporting_instance_sections", args=[self.instance.uuid]))
        self.assertEqual(resp.status_code, 200)

    def test_non_staff_redirected(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:reporting_instance_sections", args=[self.instance.uuid]))
        self.assertEqual(resp.status_code, 302)

    def test_edit_section_updates_response(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("nbms_app:reporting_instance_section_edit", args=[self.instance.uuid, self.template.code]),
            data={"summary": "Progress update"},
        )
        self.assertEqual(resp.status_code, 302)
        response = ReportSectionResponse.objects.get(reporting_instance=self.instance, template=self.template)
        self.assertEqual(response.response_json.get("summary"), "Progress update")

    def test_frozen_instance_blocks_edit(self):
        self.instance.frozen_at = timezone.now()
        self.instance.save(update_fields=["frozen_at"])
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("nbms_app:reporting_instance_section_edit", args=[self.instance.uuid, self.template.code]),
            data={"summary": "Should not save"},
        )
        self.assertEqual(resp.status_code, 403)
