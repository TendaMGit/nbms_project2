from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Methodology, MethodologyVersion, Organisation, User
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class MethodologyVersionUiTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")
        contributor_group = Group.objects.create(name=ROLE_CONTRIBUTOR)
        self.owner = User.objects.create_user(
            username="owner",
            password="pass1234",
            organisation=self.org_a,
        )
        self.owner.groups.add(contributor_group)
        self.other = User.objects.create_user(
            username="other",
            password="pass1234",
            organisation=self.org_b,
        )
        self.other.groups.add(contributor_group)
        self.methodology = Methodology.objects.create(
            methodology_code="METH-1",
            title="Methodology 1",
            owner_org=self.org_a,
        )
        self.version = MethodologyVersion.objects.create(
            methodology=self.methodology,
            version="1.0",
        )
        self.shared_methodology = Methodology.objects.create(
            methodology_code="METH-2",
            title="Methodology 2",
        )
        self.shared_version = MethodologyVersion.objects.create(
            methodology=self.shared_methodology,
            version="0.1",
        )

    def test_detail_calls_audit_and_shows_edit_for_owner(self):
        self.client.force_login(self.owner)
        with patch("nbms_app.views.audit_sensitive_access") as audit_mock:
            resp = self.client.get(
                reverse("nbms_app:methodology_version_detail", args=[self.version.uuid])
            )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.methodology.methodology_code)
        self.assertContains(resp, f"v{self.version.version}")
        self.assertContains(resp, "Edit version")
        audit_mock.assert_called_once()

    def test_detail_hidden_for_other_org(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("nbms_app:methodology_version_detail", args=[self.version.uuid]))
        self.assertEqual(resp.status_code, 404)

    def test_edit_denied_for_other_org(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("nbms_app:methodology_version_edit", args=[self.shared_version.uuid]))
        self.assertEqual(resp.status_code, 403)

    def test_list_filters_by_methodology_access(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("nbms_app:methodology_version_list"))
        self.assertContains(resp, self.shared_methodology.methodology_code)
        self.assertNotContains(resp, self.methodology.methodology_code)
