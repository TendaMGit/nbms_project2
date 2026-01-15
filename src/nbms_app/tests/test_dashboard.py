from django.test import TestCase

from nbms_app.models import LifecycleStatus, NationalTarget, Notification, Organisation, User


class DashboardTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.user = User.objects.create_user(
            username="user",
            password="pass1234",
            organisation=self.org,
        )
        self.staff = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=self.org,
            is_staff=True,
        )

    def test_dashboard_anonymous(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dashboard")
        self.assertNotContains(resp, "Pending Review")

    def test_dashboard_authenticated(self):
        Notification.objects.create(recipient=self.user, message="Test")
        self.client.force_login(self.user)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "My Drafts")
        self.assertContains(resp, "Unread: 1")
        self.assertNotContains(resp, "Pending Review")

    def test_dashboard_staff_sees_pending_review(self):
        NationalTarget.objects.create(
            code="NT1",
            title="Target",
            organisation=self.org,
            created_by=self.staff,
            status=LifecycleStatus.PENDING_REVIEW,
        )
        self.client.force_login(self.staff)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pending Review")
