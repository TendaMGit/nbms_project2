from datetime import date

from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, ReportingCycle, ReportingInstance, User


class ReportingUiTests(TestCase):
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
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

    def test_non_staff_redirected_from_cycles(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:reporting_cycle_list"))
        self.assertEqual(resp.status_code, 302)

    def test_staff_can_view_cycles_and_instance(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("nbms_app:reporting_cycle_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("nbms_app:reporting_instance_detail", args=[self.instance.uuid]))
        self.assertEqual(resp.status_code, 200)
