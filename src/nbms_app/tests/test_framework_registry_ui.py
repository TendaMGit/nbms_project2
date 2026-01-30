from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    LifecycleStatus,
    Organisation,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_ADMIN


class FrameworkRegistryUiTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.other_org = Organisation.objects.create(name="Org B")
        admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        self.catalog_admin = User.objects.create_user(
            username="catalog_admin",
            password="pass1234",
            organisation=self.org,
        )
        self.catalog_admin.groups.add(admin_group)
        self.viewer = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org,
        )
        self.other_viewer = User.objects.create_user(
            username="other_viewer",
            password="pass1234",
            organisation=self.other_org,
        )
        self.framework = Framework.objects.create(
            code="GBF",
            title="Global Biodiversity Framework",
            organisation=self.org,
            created_by=self.catalog_admin,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.goal = FrameworkGoal.objects.create(
            framework=self.framework,
            code="A",
            title="Goal A",
            sort_order=1,
        )

    def test_catalog_manager_can_access_create_and_new_buttons(self):
        self.client.force_login(self.catalog_admin)
        resp = self.client.get(reverse("nbms_app:framework_list"))
        self.assertContains(resp, "New Framework")
        resp = self.client.get(reverse("nbms_app:framework_create"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("nbms_app:framework_goal_create"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("nbms_app:framework_target_create"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("nbms_app:framework_indicator_create"))
        self.assertEqual(resp.status_code, 200)

    def test_non_privileged_blocked_from_manage_endpoints(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:framework_create"))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse("nbms_app:framework_goal_create"))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse("nbms_app:framework_target_create"))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse("nbms_app:framework_indicator_create"))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(reverse("nbms_app:framework_archive", args=[self.framework.uuid]))
        self.assertEqual(resp.status_code, 403)

    def test_archive_hides_targets_and_goals_from_default_lists(self):
        self.client.force_login(self.catalog_admin)
        target = FrameworkTarget.objects.create(
            framework=self.framework,
            goal=self.goal,
            code="T1",
            title="Target 1",
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        resp = self.client.post(reverse("nbms_app:framework_target_archive", args=[target.uuid]))
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertEqual(target.status, LifecycleStatus.ARCHIVED)
        resp = self.client.get(reverse("nbms_app:framework_target_list"))
        self.assertNotContains(resp, target.code)

        resp = self.client.post(reverse("nbms_app:framework_goal_archive", args=[self.goal.uuid]))
        self.assertEqual(resp.status_code, 302)
        self.goal.refresh_from_db()
        self.assertFalse(self.goal.is_active)
        resp = self.client.get(reverse("nbms_app:framework_goal_list"))
        self.assertNotContains(resp, self.goal.title)

    def test_goal_optional_and_cross_framework_validation(self):
        target = FrameworkTarget.objects.create(
            framework=self.framework,
            code="T2",
            title="Target 2",
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.assertIsNone(target.goal)

        framework_b = Framework.objects.create(
            code="SDG",
            title="Sustainable Development Goals",
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.client.force_login(self.catalog_admin)
        resp = self.client.post(
            reverse("nbms_app:framework_target_create"),
            {
                "framework": framework_b.id,
                "goal": self.goal.id,
                "code": "T3",
                "title": "Target 3",
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Select a valid choice")

    def test_abac_hides_internal_goal_target_indicator_from_other_org(self):
        internal_goal = FrameworkGoal.objects.create(
            framework=self.framework,
            code="B",
            title="Internal Goal",
            sort_order=2,
            organisation=self.org,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        internal_target = FrameworkTarget.objects.create(
            framework=self.framework,
            goal=internal_goal,
            code="T-INT",
            title="Internal Target",
            organisation=self.org,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        internal_indicator = FrameworkIndicator.objects.create(
            framework=self.framework,
            framework_target=internal_target,
            code="I-INT",
            title="Internal Indicator",
            organisation=self.org,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )

        self.client.force_login(self.other_viewer)
        resp = self.client.get(reverse("nbms_app:framework_goal_list"))
        self.assertNotContains(resp, internal_goal.title)
        resp = self.client.get(reverse("nbms_app:framework_target_list"))
        self.assertNotContains(resp, internal_target.code)
        resp = self.client.get(reverse("nbms_app:framework_indicator_list"))
        self.assertNotContains(resp, internal_indicator.code)

        resp = self.client.get(reverse("nbms_app:framework_goal_detail", args=[internal_goal.uuid]))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("nbms_app:framework_target_detail", args=[internal_target.uuid]))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse("nbms_app:framework_indicator_detail", args=[internal_indicator.uuid]))
        self.assertEqual(resp.status_code, 404)

    def test_admin_route_smoke(self):
        resp = self.client.get("/admin/")
        self.assertIn(resp.status_code, (200, 302))
