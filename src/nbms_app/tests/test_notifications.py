from django.test import TestCase
from django.urls import reverse

from nbms_app.models import Indicator, NationalTarget, Notification, Organisation, User
from nbms_app.services.workflows import submit_for_review


class NotificationTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.owner = User.objects.create_user(
            username="owner",
            password="pass1234",
            organisation=self.org,
        )
        target = NationalTarget.objects.create(code="NT-1", title="Target", organisation=self.org)
        self.target = Indicator.objects.create(
            code="IND-1",
            title="Indicator",
            national_target=target,
            organisation=self.org,
            created_by=self.owner,
        )

    def test_notification_created_on_submit(self):
        submit_for_review(self.target, self.owner)
        self.assertTrue(Notification.objects.filter(recipient=self.owner).exists())

    def test_notification_list_view(self):
        Notification.objects.create(recipient=self.owner, message="Test", url="")
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("nbms_app:notification_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test")
