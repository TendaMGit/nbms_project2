from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import AccessLevel, MonitoringProgramme, Organisation, SensitivityClass, User
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class MonitoringProgrammeUiTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")
        contributor_group = Group.objects.create(name=ROLE_CONTRIBUTOR)
        self.user_a = User.objects.create_user(
            username="contrib_a",
            password="pass1234",
            organisation=self.org_a,
        )
        self.user_a.groups.add(contributor_group)
        self.user_b = User.objects.create_user(
            username="contrib_b",
            password="pass1234",
            organisation=self.org_b,
        )
        self.user_b.groups.add(contributor_group)
        self.viewer = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org_b,
        )
        self.public_class = SensitivityClass.objects.create(
            sensitivity_code="PUB",
            sensitivity_name="Public",
            access_level_default=AccessLevel.PUBLIC,
        )
        self.restricted_class = SensitivityClass.objects.create(
            sensitivity_code="RES",
            sensitivity_name="Restricted",
            access_level_default=AccessLevel.RESTRICTED,
        )
        self.public_programme = MonitoringProgramme.objects.create(
            programme_code="PROG-1",
            title="Public Programme",
            lead_org=self.org_a,
            sensitivity_class=self.public_class,
        )
        self.restricted_programme = MonitoringProgramme.objects.create(
            programme_code="PROG-2",
            title="Restricted Programme",
            lead_org=self.org_a,
            sensitivity_class=self.restricted_class,
        )

    def test_list_abac_visibility(self):
        self.client.force_login(self.user_b)
        resp = self.client.get(reverse("nbms_app:monitoring_programme_list"))
        self.assertContains(resp, self.public_programme.programme_code)
        self.assertNotContains(resp, self.restricted_programme.programme_code)

    def test_detail_abac_visibility(self):
        self.client.force_login(self.user_b)
        resp = self.client.get(
            reverse("nbms_app:monitoring_programme_detail", args=[self.restricted_programme.uuid])
        )
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(
            reverse("nbms_app:monitoring_programme_detail", args=[self.public_programme.uuid])
        )
        self.assertEqual(resp.status_code, 200)

    def test_create_permission_gated(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:monitoring_programme_create"))
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("nbms_app:monitoring_programme_create"))
        self.assertEqual(resp.status_code, 200)

    def test_detail_audit_called(self):
        self.client.force_login(self.user_a)
        with patch("nbms_app.views.audit_sensitive_access") as audit_mock:
            resp = self.client.get(
                reverse("nbms_app:monitoring_programme_detail", args=[self.public_programme.uuid])
            )
        self.assertEqual(resp.status_code, 200)
        audit_mock.assert_called_once()
