from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Indicator, NationalTarget, Organisation, User


class SmokeTests(TestCase):
    def test_home_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_login_page(self):
        resp = self.client.get(reverse("admin:login"), follow=True)
        self.assertEqual(resp.status_code, 200)

    def test_health_db(self):
        resp = self.client.get(reverse("nbms_app:health_db"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("status"), "ok")

    def test_health_storage(self):
        resp = self.client.get(reverse("nbms_app:health_storage"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("status", resp.json())

    def test_indicator_create(self):
        target = NationalTarget.objects.create(code="NT1", title="National Target 1")
        indicator = Indicator.objects.create(code="IND1", title="Indicator 1", national_target=target)
        self.assertEqual(indicator.national_target, target)

    def test_user_org_relation(self):
        org = Organisation.objects.create(name="NBMS Org")
        user = User.objects.create_user(username="tester", password="pass1234", organisation=org)
        self.assertEqual(user.organisation, org)
