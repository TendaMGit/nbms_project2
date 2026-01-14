from datetime import date

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from nbms_app.models import (
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    User,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.instance_approvals import (
    approve_for_instance,
    approved_queryset,
    is_approved_for_instance,
    revoke_for_instance,
)


class InstanceApprovalTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance_a = ReportingInstance.objects.create(cycle=self.cycle, version_label="A")
        self.instance_b = ReportingInstance.objects.create(cycle=self.cycle, version_label="B")
        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
        )
        self.reviewer = User.objects.create_user(username="reviewer", password="pass1234", organisation=self.org)
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.viewer = User.objects.create_user(username="viewer", password="pass1234", organisation=self.org)

    def test_approval_is_instance_scoped(self):
        approve_for_instance(self.instance_a, self.target, self.reviewer)
        self.assertTrue(is_approved_for_instance(self.instance_a, self.target))
        self.assertFalse(is_approved_for_instance(self.instance_b, self.target))
        approved = approved_queryset(self.instance_a, NationalTarget)
        self.assertIn(self.target, list(approved))

    def test_unauthorized_users_cannot_approve_or_revoke(self):
        with self.assertRaises(PermissionDenied):
            approve_for_instance(self.instance_a, self.target, self.viewer)
        approve_for_instance(self.instance_a, self.target, self.reviewer)
        with self.assertRaises(PermissionDenied):
            revoke_for_instance(self.instance_a, self.target, self.viewer)
