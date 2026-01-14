from django.contrib.auth.models import Group
from django.test import TestCase

from nbms_app.models import AuditEvent, Indicator, LifecycleStatus, NationalTarget, Organisation, SensitivityLevel, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.workflows import approve, submit_for_review


class AuditEventTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.owner = User.objects.create_user(
            username="owner",
            password="pass1234",
            organisation=self.org,
        )
        self.reviewer = User.objects.create_user(
            username="reviewer",
            password="pass1234",
            organisation=self.org,
        )
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))

    def test_workflow_creates_audit_event(self):
        target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
            created_by=self.owner,
        )
        submit_for_review(target, self.owner)
        approve(target, self.reviewer, note="ok")
        self.assertTrue(AuditEvent.objects.filter(action="submit_for_review").exists())
        event = AuditEvent.objects.filter(action="approve").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata.get("note"), "ok")

    def test_sensitive_field_change_audited(self):
        target = NationalTarget.objects.create(
            code="NT-2",
            title="Target 2",
            organisation=self.org,
            created_by=self.owner,
        )
        target.sensitivity = SensitivityLevel.RESTRICTED
        target.save()
        event = AuditEvent.objects.filter(action="update_nationaltarget").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata.get("sensitivity"), SensitivityLevel.RESTRICTED)

    def test_indicator_update_audit(self):
        target = NationalTarget.objects.create(
            code="NT-3",
            title="Target 3",
            organisation=self.org,
            created_by=self.owner,
        )
        indicator = Indicator.objects.create(
            code="IND-1",
            title="Indicator",
            national_target=target,
            organisation=self.org,
            created_by=self.owner,
            status=LifecycleStatus.DRAFT,
        )
        indicator.status = LifecycleStatus.PENDING_REVIEW
        indicator.save()
        event = AuditEvent.objects.filter(action="update_indicator").first()
        self.assertIsNotNone(event)
