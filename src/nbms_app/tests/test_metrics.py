from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from nbms_app.models import Organisation, User
from nbms_app.services.authorization import ROLE_SYSTEM_ADMIN


class MetricsAccessTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.staff_user = User.objects.create_user(
            username="staff",
            password="pass1234",
            is_staff=True,
            organisation=self.org,
        )
        system_group, _ = Group.objects.get_or_create(name=ROLE_SYSTEM_ADMIN)
        self.staff_user.groups.add(system_group)

    def test_anonymous_blocked(self):
        resp = self.client.get(reverse("nbms_app:metrics"))
        self.assertEqual(resp.status_code, 403)

    def test_staff_allowed(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse("nbms_app:metrics"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("requests_total", resp.content.decode())

    @override_settings(METRICS_TOKEN="metrics-secret")
    def test_bearer_token_allowed_for_anonymous(self):
        resp = self.client.get(
            reverse("nbms_app:metrics"),
            HTTP_AUTHORIZATION="Bearer metrics-secret",
        )
        self.assertEqual(resp.status_code, 200)

    @override_settings(METRICS_TOKEN="metrics-secret")
    def test_query_token_blocked_by_default(self):
        resp = self.client.get(reverse("nbms_app:metrics"), {"token": "metrics-secret"})
        self.assertEqual(resp.status_code, 403)

    @override_settings(METRICS_TOKEN="metrics-secret", METRICS_ALLOW_QUERY_TOKEN=True)
    def test_query_token_allowed_when_explicitly_enabled(self):
        resp = self.client.get(reverse("nbms_app:metrics"), {"token": "metrics-secret"})
        self.assertEqual(resp.status_code, 200)
