from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    AccessLevel,
    DatasetCatalog,
    Evidence,
    Indicator,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_SYSTEM_ADMIN


class AbacViewTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")

        self.creator = User.objects.create_user(
            username="creator",
            password="pass1234",
            organisation=self.org_a,
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="pass1234",
            organisation=self.org_b,
        )
        self.staff_user = User.objects.create_user(
            username="staff-user",
            password="pass1234",
            organisation=self.org_a,
            is_staff=True,
        )
        self.system_admin = User.objects.create_user(
            username="sysadmin",
            password="pass1234",
            organisation=self.org_b,
        )
        self.system_admin.groups.add(Group.objects.create(name=ROLE_SYSTEM_ADMIN))

        self.target_public = NationalTarget.objects.create(
            code="NT-PUB",
            title="Public",
            organisation=self.org_a,
            created_by=self.creator,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.target_internal = NationalTarget.objects.create(
            code="NT-INT",
            title="Internal",
            organisation=self.org_b,
            created_by=self.other_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        self.target_restricted = NationalTarget.objects.create(
            code="NT-RES",
            title="Restricted",
            organisation=self.org_b,
            created_by=self.other_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.RESTRICTED,
        )
        self.target_iplc = NationalTarget.objects.create(
            code="NT-IPLC",
            title="IPLC",
            organisation=self.org_b,
            created_by=self.other_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )

        self.indicator_public = Indicator.objects.create(
            code="IND-PUB",
            title="Public Indicator",
            national_target=self.target_public,
            organisation=self.org_a,
            created_by=self.creator,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

        self.evidence_public = Evidence.objects.create(
            title="Public Evidence",
            organisation=self.org_a,
            created_by=self.creator,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.evidence_internal = Evidence.objects.create(
            title="Internal Evidence",
            organisation=self.org_b,
            created_by=self.other_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )

        self.dataset_public = DatasetCatalog.objects.create(
            dataset_code="DS-PUB",
            title="Public Dataset",
            access_level=AccessLevel.PUBLIC,
            custodian_org=self.org_a,
            is_active=True,
        )
        self.dataset_internal = DatasetCatalog.objects.create(
            dataset_code="DS-INT",
            title="Internal Dataset",
            access_level=AccessLevel.INTERNAL,
            custodian_org=self.org_b,
            is_active=True,
        )

    def test_anonymous_sees_only_public_targets(self):
        resp = self.client.get(reverse("nbms_app:national_target_list"))
        targets = list(resp.context["targets"])
        self.assertIn(self.target_public, targets)
        self.assertNotIn(self.target_internal, targets)

    def test_anonymous_target_detail_blocked(self):
        resp = self.client.get(
            reverse("nbms_app:national_target_detail", args=[self.target_internal.uuid])
        )
        self.assertEqual(resp.status_code, 404)

    def test_system_admin_can_view_restricted_and_iplc(self):
        self.client.force_login(self.system_admin)
        resp = self.client.get(
            reverse("nbms_app:national_target_detail", args=[self.target_restricted.uuid])
        )
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(
            reverse("nbms_app:national_target_detail", args=[self.target_iplc.uuid])
        )
        self.assertEqual(resp.status_code, 200)

    def test_staff_without_system_admin_cannot_view_iplc(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(
            reverse("nbms_app:national_target_detail", args=[self.target_iplc.uuid])
        )
        self.assertEqual(resp.status_code, 404)

    def test_indicator_list_anonymous_public_only(self):
        resp = self.client.get(reverse("nbms_app:indicator_list"))
        indicators = list(resp.context["indicators"])
        self.assertIn(self.indicator_public, indicators)

    def test_indicator_detail_anonymous_public(self):
        resp = self.client.get(reverse("nbms_app:indicator_detail", args=[self.indicator_public.uuid]))
        self.assertEqual(resp.status_code, 200)

    def test_evidence_list_anonymous_public_only(self):
        resp = self.client.get(reverse("nbms_app:evidence_list"))
        evidence_items = list(resp.context["evidence_items"])
        self.assertIn(self.evidence_public, evidence_items)
        self.assertNotIn(self.evidence_internal, evidence_items)

    def test_evidence_detail_anonymous_blocked(self):
        resp = self.client.get(reverse("nbms_app:evidence_detail", args=[self.evidence_internal.uuid]))
        self.assertEqual(resp.status_code, 404)

    def test_dataset_list_anonymous_public_only(self):
        resp = self.client.get(reverse("nbms_app:dataset_list"))
        datasets = list(resp.context["datasets"])
        self.assertIn(self.dataset_public, datasets)
        self.assertNotIn(self.dataset_internal, datasets)

    def test_dataset_detail_anonymous_blocked(self):
        resp = self.client.get(reverse("nbms_app:dataset_detail", args=[self.dataset_internal.uuid]))
        self.assertEqual(resp.status_code, 404)
