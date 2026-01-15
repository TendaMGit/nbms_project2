from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import AuditEvent, NationalTarget, Organisation, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.workflows import submit_for_review


class AuditEventViewTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.staff_user = User.objects.create_user(
            username="staff",
            password="pass1234",
            is_staff=True,
            organisation=self.org,
        )
        self.staff_user.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.non_staff = User.objects.create_user(username="user", password="pass1234")

    def test_staff_can_view_audit_events(self):
        target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
            created_by=self.staff_user,
        )
        submit_for_review(target, self.staff_user)
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse("nbms_app:audit_event_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.context["events"]), 1)

    def test_non_staff_blocked(self):
        self.client.force_login(self.non_staff)
        resp = self.client.get(reverse("nbms_app:audit_event_list"))
        self.assertEqual(resp.status_code, 302)

    def test_audit_event_metadata(self):
        target = NationalTarget.objects.create(
            code="NT-2",
            title="Target 2",
            organisation=self.org,
            created_by=self.staff_user,
        )
        submit_for_review(target, self.staff_user)
        event = AuditEvent.objects.filter(action="submit_for_review").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata.get("status"), "pending_review")
