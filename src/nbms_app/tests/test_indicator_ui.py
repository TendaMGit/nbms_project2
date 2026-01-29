from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    QaStatus,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_CONTRIBUTOR


class IndicatorUiTests(TestCase):
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
        self.target = NationalTarget.objects.create(
            code="NT1",
            title="Target",
            organisation=self.org,
            created_by=self.contributor,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

    def test_contributor_can_create_indicator(self):
        self.client.force_login(self.contributor)
        resp = self.client.post(
            reverse("nbms_app:indicator_create"),
            {
                "code": "IND1",
                "title": "Indicator 1",
                "national_target": self.target.id,
                "indicator_type": NationalIndicatorType.OTHER,
                "qa_status": QaStatus.DRAFT,
                "sensitivity": SensitivityLevel.INTERNAL,
            },
        )
        self.assertEqual(resp.status_code, 302)
        indicator = Indicator.objects.get(code="IND1")
        self.assertEqual(indicator.created_by, self.contributor)

    def test_non_contributor_blocked_from_create(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:indicator_create"))
        self.assertEqual(resp.status_code, 403)

    def test_edit_locked_when_pending_review(self):
        indicator = Indicator.objects.create(
            code="IND2",
            title="Indicator 2",
            national_target=self.target,
            organisation=self.org,
            created_by=self.contributor,
            status=LifecycleStatus.PENDING_REVIEW,
        )
        self.client.force_login(self.contributor)
        resp = self.client.get(reverse("nbms_app:indicator_edit", args=[indicator.uuid]))
        self.assertEqual(resp.status_code, 403)

    def test_empty_state_shows_create_button(self):
        self.client.force_login(self.contributor)
        resp = self.client.get(reverse("nbms_app:indicator_list"))
        self.assertContains(resp, "Create Indicator")
