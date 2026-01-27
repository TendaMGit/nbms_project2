from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.urls import reverse

from nbms_app.admin import (
    FrameworkAdmin,
    FrameworkGoalAdmin,
    FrameworkIndicatorAdmin,
    FrameworkTargetAdmin,
)
from nbms_app.forms_catalog import (
    FRAMEWORK_GOAL_READONLY_FIELDS,
    FRAMEWORK_INDICATOR_READONLY_FIELDS,
    FRAMEWORK_READONLY_FIELDS,
    FRAMEWORK_TARGET_READONLY_FIELDS,
    FrameworkCatalogForm,
    FrameworkGoalCatalogForm,
    FrameworkIndicatorCatalogForm,
    FrameworkTargetCatalogForm,
    build_readonly_panel,
)
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


class CatalogAdminParityTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
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
        self.superuser = User.objects.create_superuser(
            username="superuser",
            password="pass1234",
            email="super@example.com",
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

    def _admin_request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def test_admin_and_site_form_field_parity(self):
        admin_site = AdminSite()
        admin_pairs = [
            (FrameworkAdmin, Framework, FrameworkCatalogForm),
            (FrameworkGoalAdmin, FrameworkGoal, FrameworkGoalCatalogForm),
            (FrameworkTargetAdmin, FrameworkTarget, FrameworkTargetCatalogForm),
            (FrameworkIndicatorAdmin, FrameworkIndicator, FrameworkIndicatorCatalogForm),
        ]
        request = self._admin_request(self.superuser)
        for admin_cls, model, form_cls in admin_pairs:
            admin_instance = admin_cls(model, admin_site)
            admin_form = admin_instance.get_form(request)
            admin_fields = list(admin_form.base_fields.keys())
            site_fields = list(form_cls.base_fields.keys())
            self.assertEqual(admin_fields, site_fields)

    def test_admin_readonly_fields_match_catalog_constants(self):
        admin_site = AdminSite()
        request = self._admin_request(self.superuser)
        admin_instance = FrameworkAdmin(Framework, admin_site)
        self.assertEqual(tuple(admin_instance.get_readonly_fields(request)), FRAMEWORK_READONLY_FIELDS)
        admin_instance = FrameworkGoalAdmin(FrameworkGoal, admin_site)
        self.assertEqual(tuple(admin_instance.get_readonly_fields(request)), FRAMEWORK_GOAL_READONLY_FIELDS)
        admin_instance = FrameworkTargetAdmin(FrameworkTarget, admin_site)
        self.assertEqual(tuple(admin_instance.get_readonly_fields(request)), FRAMEWORK_TARGET_READONLY_FIELDS)
        admin_instance = FrameworkIndicatorAdmin(FrameworkIndicator, admin_site)
        self.assertEqual(tuple(admin_instance.get_readonly_fields(request)), FRAMEWORK_INDICATOR_READONLY_FIELDS)

    def test_readonly_panel_rendered_on_edit(self):
        self.client.force_login(self.catalog_admin)
        resp = self.client.get(reverse("nbms_app:framework_edit", args=[self.framework.uuid]))
        self.assertEqual(resp.status_code, 200)
        readonly = build_readonly_panel(self.framework, FRAMEWORK_READONLY_FIELDS)
        for item in readonly:
            label = str(item["label"])
            expected = f"{label[:1].upper()}{label[1:]}"
            self.assertContains(resp, expected)
        self.assertNotContains(resp, 'name="uuid"')

    def test_non_manager_blocked_from_site_catalog_endpoints(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:framework_create"))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse("nbms_app:framework_edit", args=[self.framework.uuid]))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(reverse("nbms_app:framework_archive", args=[self.framework.uuid]))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse("nbms_app:framework_list"))
        self.assertNotContains(resp, "New Framework")

    def test_admin_delete_disabled(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("admin:nbms_app_framework_delete", args=[self.framework.id]))
        self.assertEqual(resp.status_code, 403)
        admin_site = AdminSite()
        request = self._admin_request(self.superuser)
        admin_instance = FrameworkAdmin(Framework, admin_site)
        actions = admin_instance.get_actions(request)
        self.assertNotIn("delete_selected", actions)

    def test_archive_via_site_and_admin(self):
        self.client.force_login(self.catalog_admin)
        resp = self.client.post(reverse("nbms_app:framework_archive", args=[self.framework.uuid]))
        self.assertEqual(resp.status_code, 302)
        self.framework.refresh_from_db()
        self.assertEqual(self.framework.status, LifecycleStatus.ARCHIVED)
        resp = self.client.get(reverse("nbms_app:framework_list"))
        self.assertNotContains(resp, self.framework.code)

        framework_b = Framework.objects.create(
            code="SDG",
            title="Sustainable Development Goals",
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse("admin:nbms_app_framework_changelist"),
            {
                "action": "archive_selected",
                "_selected_action": [str(framework_b.id)],
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        framework_b.refresh_from_db()
        self.assertEqual(framework_b.status, LifecycleStatus.ARCHIVED)
        resp = self.client.get(reverse("admin:nbms_app_framework_changelist"))
        self.assertNotContains(resp, framework_b.code)
