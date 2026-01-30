from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Methodology, Organisation, User
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class MethodologyUiTests(TestCase):
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
        self.owned_methodology = Methodology.objects.create(
            methodology_code="METH-1",
            title="Owned Methodology",
            owner_org=self.org_a,
        )
        self.shared_methodology = Methodology.objects.create(
            methodology_code="METH-2",
            title="Shared Methodology",
        )

    def test_list_abac_visibility(self):
        self.client.force_login(self.user_b)
        resp = self.client.get(reverse("nbms_app:methodology_list"))
        self.assertContains(resp, self.shared_methodology.methodology_code)
        self.assertNotContains(resp, self.owned_methodology.methodology_code)

    def test_detail_abac_visibility(self):
        self.client.force_login(self.user_b)
        resp = self.client.get(reverse("nbms_app:methodology_detail", args=[self.owned_methodology.uuid]))
        self.assertEqual(resp.status_code, 404)

    def test_detail_audit_called(self):
        self.client.force_login(self.user_a)
        with patch("nbms_app.views.audit_sensitive_access") as audit_mock:
            resp = self.client.get(reverse("nbms_app:methodology_detail", args=[self.owned_methodology.uuid]))
        self.assertEqual(resp.status_code, 200)
        audit_mock.assert_called_once()

    def test_create_permission_gated(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:methodology_create"))
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.user_a)
        resp = self.client.get(reverse("nbms_app:methodology_create"))
        self.assertEqual(resp.status_code, 200)

    def test_edit_permission_gated(self):
        self.client.force_login(self.user_b)
        resp = self.client.get(reverse("nbms_app:methodology_edit", args=[self.shared_methodology.uuid]))
        self.assertEqual(resp.status_code, 403)
