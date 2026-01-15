from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, User


class MetricsAccessTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.staff_user = User.objects.create_user(
            username="staff",
            password="pass1234",
            is_staff=True,
            organisation=self.org,
        )

    def test_anonymous_blocked(self):
        resp = self.client.get(reverse("nbms_app:metrics"))
        self.assertEqual(resp.status_code, 403)

    def test_staff_allowed(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse("nbms_app:metrics"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("requests_total", resp.content.decode())
