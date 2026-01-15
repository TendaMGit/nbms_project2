from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, User
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class DomainViewPermissionTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.contributor = User.objects.create_user(
            username="contrib",
            password="pass1234",
            organisation=self.org,
        )
        self.contributor.groups.add(Group.objects.create(name=ROLE_CONTRIBUTOR))
        self.viewer = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org,
        )

    def test_contributor_can_access_evidence_create(self):
        self.client.force_login(self.contributor)
        resp = self.client.get(reverse("nbms_app:evidence_create"))
        self.assertEqual(resp.status_code, 200)

    def test_non_contributor_blocked_evidence_create(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:evidence_create"))
        self.assertEqual(resp.status_code, 403)

    def test_contributor_can_access_dataset_create(self):
        self.client.force_login(self.contributor)
        resp = self.client.get(reverse("nbms_app:dataset_create"))
        self.assertEqual(resp.status_code, 200)

    def test_non_contributor_blocked_dataset_create(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:dataset_create"))
        self.assertEqual(resp.status_code, 403)
