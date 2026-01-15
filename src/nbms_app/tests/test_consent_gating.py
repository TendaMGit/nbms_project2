from datetime import date

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from nbms_app.models import AuditEvent, NationalTarget, Notification, Organisation, ReportingCycle, ReportingInstance, SensitivityLevel, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.instance_approvals import approve_for_instance


class ConsentGatingTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.reviewer = User.objects.create_user(username="reviewer", password="pass1234", organisation=self.org)
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")
        self.target = NationalTarget.objects.create(
            code="NT-IPLC",
            title="IPLC Target",
            organisation=self.org,
            created_by=self.reviewer,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )

    def test_approval_blocked_without_consent(self):
        with self.assertRaises(PermissionDenied):
            approve_for_instance(self.instance, self.target, self.reviewer)
        self.assertTrue(
            AuditEvent.objects.filter(object_uuid=self.target.uuid, action="instance_export_blocked_consent").exists()
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.reviewer, message__icontains="Approval blocked").exists()
        )
