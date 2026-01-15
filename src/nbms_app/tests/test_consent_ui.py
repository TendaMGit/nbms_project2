from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_COMMUNITY_REPRESENTATIVE


class ConsentUiTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")
        self.community_rep = User.objects.create_user(
            username="rep",
            password="pass1234",
            organisation=self.org_a,
        )
        self.community_rep.groups.add(Group.objects.create(name=ROLE_COMMUNITY_REPRESENTATIVE))
        self.viewer = User.objects.create_user(username="viewer", password="pass1234", organisation=self.org_a)
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")
        self.target = NationalTarget.objects.create(
            code="NT-IPLC",
            title="IPLC Target",
            organisation=self.org_a,
            created_by=self.community_rep,
            status="published",
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )
        self.other_target = NationalTarget.objects.create(
            code="NT-OTHER",
            title="Other Target",
            organisation=self.org_b,
            created_by=self.viewer,
            status="published",
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )

    def test_access_control_requires_consent_role(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:reporting_instance_consent", args=[self.instance.uuid]))
        self.assertEqual(resp.status_code, 403)

    def test_community_rep_can_grant_consent(self):
        self.client.force_login(self.community_rep)
        resp = self.client.post(
            reverse(
                "nbms_app:reporting_instance_consent_action",
                args=[self.instance.uuid, "target", self.target.uuid, "grant"],
            ),
            {"note": "ok"},
        )
        self.assertEqual(resp.status_code, 302)
        record = ConsentRecord.objects.get(
            reporting_instance=self.instance,
            object_uuid=self.target.uuid,
        )
        self.assertEqual(record.status, ConsentStatus.GRANTED)

    def test_abac_filters_consent_workspace(self):
        self.client.force_login(self.community_rep)
        resp = self.client.get(reverse("nbms_app:reporting_instance_consent", args=[self.instance.uuid]))
        self.assertContains(resp, self.target.code)
        self.assertNotContains(resp, self.other_target.code)
