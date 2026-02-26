from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nbms_app.models import (
    ApprovalDecision,
    AuditEvent,
    InstanceExportApproval,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    User,
)
from nbms_app.services.authorization import ROLE_ADMIN, ROLE_SYSTEM_ADMIN


class ReportingFreezeTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.owner = User.objects.create_user(username="owner", password="pass1234", organisation=self.org)
        self.admin = User.objects.create_user(
            username="admin",
            password="pass1234",
            organisation=self.org,
            is_staff=True,
        )
        admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        system_group, _ = Group.objects.get_or_create(name=ROLE_SYSTEM_ADMIN)
        self.admin.groups.add(admin_group)
        self.admin.groups.add(system_group)
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(
            cycle=self.cycle,
            version_label="v1",
            frozen_at=timezone.now(),
            frozen_by=self.admin,
        )
        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
            created_by=self.owner,
            status=LifecycleStatus.PUBLISHED,
        )

    def test_freeze_blocks_non_admin_approvals(self):
        self.client.force_login(self.owner)
        url = reverse(
            "nbms_app:reporting_instance_approval_action",
            args=[self.instance.uuid, "target", self.target.uuid, "approve"],
        )
        resp = self.client.post(url, {"note": "ok"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            InstanceExportApproval.objects.filter(reporting_instance=self.instance, object_uuid=self.target.uuid).exists()
        )

    def test_admin_override_allows_approval(self):
        self.client.force_login(self.admin)
        url = reverse(
            "nbms_app:reporting_instance_approval_action",
            args=[self.instance.uuid, "target", self.target.uuid, "approve"],
        )
        resp = self.client.post(url, {"note": "ok", "admin_override": "1"})
        self.assertEqual(resp.status_code, 302)
        approval = InstanceExportApproval.objects.get(
            reporting_instance=self.instance,
            object_uuid=self.target.uuid,
        )
        self.assertEqual(approval.decision, ApprovalDecision.APPROVED)
        self.assertTrue(
            AuditEvent.objects.filter(object_uuid=self.target.uuid, action="instance_export_override").exists()
        )
