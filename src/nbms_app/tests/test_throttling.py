from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from nbms_app.models import LifecycleStatus, NationalTarget, Organisation, SensitivityLevel, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD


class ThrottlingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = Organisation.objects.create(name="Org A")
        self.reviewer = User.objects.create_user(
            username="reviewer",
            password="pass1234",
            is_staff=True,
            organisation=self.org,
        )
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
            status=LifecycleStatus.PENDING_REVIEW,
            sensitivity=SensitivityLevel.INTERNAL,
        )

    @override_settings(
        RATE_LIMITS={
            "workflow": {
                "rate": "1/60",
                "methods": ["POST"],
                "paths": ["/manage/review-queue/"],
                "actions": ["approve"],
            }
        }
    )
    def test_workflow_throttling(self):
        self.client.force_login(self.reviewer)
        url = reverse("nbms_app:review_action", args=["target", self.target.uuid, "approve"])
        resp1 = self.client.post(url, {"note": "ok"})
        resp2 = self.client.post(url, {"note": "ok"})
        self.assertNotEqual(resp1.status_code, 429)
        self.assertEqual(resp2.status_code, 429)
