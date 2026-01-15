from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Organisation, User
from nbms_app.roles import CANONICAL_GROUPS


class UserManagementTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff",
            password="pass1234",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(username="regular", password="pass1234")
        self.org = Organisation.objects.create(name="Org A")
        self.group = Group.objects.create(name=CANONICAL_GROUPS[0])

    def test_staff_can_view_list(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse("nbms_app:manage_user_list"))
        self.assertEqual(resp.status_code, 200)

    def test_non_staff_blocked(self):
        self.client.force_login(self.regular_user)
        resp = self.client.get(reverse("nbms_app:manage_user_list"))
        self.assertEqual(resp.status_code, 302)

    def test_create_user(self):
        self.client.force_login(self.staff_user)
        resp = self.client.post(
            reverse("nbms_app:manage_user_create"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "organisation": self.org.id,
                "groups": [str(self.group.id)],
                "is_active": "on",
                "password1": "Secret123",
                "password2": "Secret123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.organisation, self.org)
        self.assertTrue(user.groups.filter(id=self.group.id).exists())

    def test_edit_user_toggle_active(self):
        user = User.objects.create_user(
            username="toggle",
            password="pass1234",
            email="toggle@example.com",
            organisation=self.org,
            is_active=True,
        )
        self.client.force_login(self.staff_user)
        resp = self.client.post(
            reverse("nbms_app:manage_user_edit", args=[user.id]),
            {
                "username": "toggle",
                "email": "toggle@example.com",
                "first_name": "",
                "last_name": "",
                "organisation": self.org.id,
                "groups": [str(self.group.id)],
            },
        )
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(user.groups.filter(id=self.group.id).exists())

    def test_send_password_reset(self):
        user = User.objects.create_user(
            username="reset",
            password="pass1234",
            email="reset@example.com",
        )
        self.client.force_login(self.staff_user)
        resp = self.client.post(reverse("nbms_app:manage_user_send_reset", args=[user.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
