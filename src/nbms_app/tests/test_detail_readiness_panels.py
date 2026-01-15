from datetime import date

from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Indicator, NationalTarget, Organisation, ReportingCycle, ReportingInstance, User


class DetailReadinessPanelTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.user = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org,
        )
        self.staff = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=self.org,
            is_staff=True,
        )
        self.target = NationalTarget.objects.create(
            code="NT-10",
            title="Target 10",
            organisation=self.org,
            created_by=self.user,
        )
        self.indicator = Indicator.objects.create(
            code="IND-10",
            title="Indicator 10",
            national_target=self.target,
            organisation=self.org,
            created_by=self.user,
        )
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-CTX",
            title="Cycle Context",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

    def test_indicator_readiness_requires_instance_in_session(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("nbms_app:indicator_detail", args=[self.indicator.uuid]))
        self.assertContains(resp, "Set a current reporting instance")

        session = self.client.session
        session["current_reporting_instance_uuid"] = str(self.instance.uuid)
        session.save()
        resp = self.client.get(reverse("nbms_app:indicator_detail", args=[self.indicator.uuid]))
        self.assertContains(resp, "Current instance")
