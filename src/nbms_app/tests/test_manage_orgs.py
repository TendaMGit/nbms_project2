from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, User


class OrganisationManagementTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff",
            password="pass1234",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(username="regular", password="pass1234")

    def test_staff_can_view_list(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse("nbms_app:manage_organisation_list"))
        self.assertEqual(resp.status_code, 200)

    def test_non_staff_blocked(self):
        self.client.force_login(self.regular_user)
        resp = self.client.get(reverse("nbms_app:manage_organisation_list"))
        self.assertEqual(resp.status_code, 302)

    def test_create_organisation(self):
        self.client.force_login(self.staff_user)
        resp = self.client.post(
            reverse("nbms_app:manage_organisation_create"),
            {
                "name": "Org A",
                "org_type": "Government",
                "contact_email": "org@example.com",
                "is_active": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Organisation.objects.filter(name="Org A").exists())

    def test_edit_organisation(self):
        org = Organisation.objects.create(name="Org B", org_type="NGO", contact_email="old@example.com")
        self.client.force_login(self.staff_user)
        resp = self.client.post(
            reverse("nbms_app:manage_organisation_edit", args=[org.id]),
            {
                "name": "Org B Updated",
                "org_type": "NGO",
                "contact_email": "new@example.com",
                "is_active": "on",
            },
        )
        self.assertEqual(resp.status_code, 302)
        org.refresh_from_db()
        self.assertEqual(org.name, "Org B Updated")
