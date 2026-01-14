from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, User


class SmokeTests(TestCase):
    def test_home_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_user_org_relation(self):
        org = Organisation.objects.create(name="NBMS Org")
        user = User.objects.create_user(username="tester", password="pass1234", organisation=org)
        self.assertEqual(user.organisation, org)
