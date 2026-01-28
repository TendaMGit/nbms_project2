from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import LifecycleStatus, NationalTarget, Organisation, QaStatus, SensitivityLevel, User
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class NationalTargetUiTests(TestCase):
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

    def test_contributor_can_create_target(self):
        self.client.force_login(self.contributor)
        resp = self.client.post(
            reverse("nbms_app:national_target_create"),
            {
                "code": "NT1",
                "title": "Target 1",
                "description": "",
                "sensitivity": SensitivityLevel.INTERNAL,
                "qa_status": QaStatus.DRAFT,
            },
        )
        self.assertEqual(resp.status_code, 302)
        target = NationalTarget.objects.get(code="NT1")
        self.assertEqual(target.created_by, self.contributor)

    def test_non_contributor_blocked_from_create(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:national_target_create"))
        self.assertEqual(resp.status_code, 403)

    def test_edit_locked_when_pending_review(self):
        target = NationalTarget.objects.create(
            code="NT2",
            title="Target 2",
            organisation=self.org,
            created_by=self.contributor,
            status=LifecycleStatus.PENDING_REVIEW,
        )
        self.client.force_login(self.contributor)
        resp = self.client.get(reverse("nbms_app:national_target_edit", args=[target.uuid]))
        self.assertEqual(resp.status_code, 403)

    def test_empty_state_shows_create_button(self):
        self.client.force_login(self.contributor)
        resp = self.client.get(reverse("nbms_app:national_target_list"))
        self.assertContains(resp, "Create National Target")
