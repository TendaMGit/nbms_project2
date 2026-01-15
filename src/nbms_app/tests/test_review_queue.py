from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Indicator, LifecycleStatus, NationalTarget, Organisation, SensitivityLevel, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD


class ReviewQueueViewTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.reviewer = User.objects.create_user(
            username="reviewer",
            password="pass1234",
            is_staff=True,
            organisation=self.org,
        )
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.non_staff = User.objects.create_user(username="user", password="pass1234")

        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
            status=LifecycleStatus.PENDING_REVIEW,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        self.indicator = Indicator.objects.create(
            code="IND-1",
            title="Indicator",
            national_target=self.target,
            organisation=self.org,
            status=LifecycleStatus.PENDING_REVIEW,
            sensitivity=SensitivityLevel.INTERNAL,
        )

    def test_staff_can_view_queue(self):
        self.client.force_login(self.reviewer)
        resp = self.client.get(reverse("nbms_app:review_queue"))
        self.assertEqual(resp.status_code, 200)

    def test_non_staff_blocked(self):
        self.client.force_login(self.non_staff)
        resp = self.client.get(reverse("nbms_app:review_queue"))
        self.assertEqual(resp.status_code, 302)

    def test_approve_action(self):
        self.client.force_login(self.reviewer)
        resp = self.client.post(
            reverse("nbms_app:review_action", args=["target", self.target.uuid, "approve"]),
            {"note": "ok"},
        )
        self.assertEqual(resp.status_code, 302)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, LifecycleStatus.APPROVED)

    def test_reject_action(self):
        self.client.force_login(self.reviewer)
        resp = self.client.post(
            reverse("nbms_app:review_action", args=["indicator", self.indicator.uuid, "reject"]),
            {"note": "needs fixes"},
        )
        self.assertEqual(resp.status_code, 302)
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.status, LifecycleStatus.DRAFT)
        self.assertEqual(self.indicator.review_note, "needs fixes")
