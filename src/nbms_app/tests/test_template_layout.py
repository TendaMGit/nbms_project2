from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, User


class TemplateLayoutTests(TestCase):
    def test_indicator_list_uses_base_layout(self):
        resp = self.client.get(reverse("nbms_app:indicator_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Home")
        self.assertContains(resp, "Indicators")

    def test_staff_nav_links_visible(self):
        org = Organisation.objects.create(name="Org A")
        staff = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=org,
            is_staff=True,
        )
        self.client.force_login(staff)
        resp = self.client.get(reverse("nbms_app:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Manage Orgs")
