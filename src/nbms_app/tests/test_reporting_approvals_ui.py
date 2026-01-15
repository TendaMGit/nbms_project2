from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    ApprovalDecision,
    AuditEvent,
    Indicator,
    InstanceExportApproval,
    NationalTarget,
    Notification,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    User,
    LifecycleStatus,
    SensitivityLevel,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD


class ReportingApprovalsUiTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")
        self.owner = User.objects.create_user(
            username="owner",
            password="pass1234",
            organisation=self.org_a,
        )
        self.reviewer = User.objects.create_user(
            username="reviewer",
            password="pass1234",
            organisation=self.org_a,
        )
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.viewer = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org_a,
        )
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")
        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org_a,
            created_by=self.owner,
        )
        self.indicator = Indicator.objects.create(
            code="IND-1",
            title="Indicator",
            national_target=self.target,
            organisation=self.org_a,
            created_by=self.owner,
        )
        self.other_target = NationalTarget.objects.create(
            code="NT-2",
            title="Other",
            organisation=self.org_b,
            created_by=self.viewer,
        )

    def test_access_control_requires_approval_role(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:reporting_instance_approvals", args=[self.instance.uuid]))
        self.assertEqual(resp.status_code, 403)

    def test_abac_filtering_applies(self):
        self.client.force_login(self.reviewer)
        resp = self.client.get(reverse("nbms_app:reporting_instance_approvals", args=[self.instance.uuid]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.indicator.code)
        self.assertNotContains(resp, self.other_target.code)

    def test_approve_and_revoke_creates_audit_and_notification(self):
        self.client.force_login(self.reviewer)
        approve_url = reverse(
            "nbms_app:reporting_instance_approval_action",
            args=[self.instance.uuid, "indicator", self.indicator.uuid, "approve"],
        )
        resp = self.client.post(approve_url, {"note": "ok"})
        self.assertEqual(resp.status_code, 302)
        approval = InstanceExportApproval.objects.get(
            reporting_instance=self.instance,
            object_uuid=self.indicator.uuid,
        )
        self.assertEqual(approval.decision, ApprovalDecision.APPROVED)
        self.assertTrue(
            AuditEvent.objects.filter(object_uuid=self.indicator.uuid, action="instance_export_approve").exists()
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.owner, message__icontains="Export approved").exists()
        )

        revoke_url = reverse(
            "nbms_app:reporting_instance_approval_action",
            args=[self.instance.uuid, "indicator", self.indicator.uuid, "revoke"],
        )
        resp = self.client.post(revoke_url, {"note": "revoke"})
        self.assertEqual(resp.status_code, 302)
        approval.refresh_from_db()
        self.assertEqual(approval.decision, ApprovalDecision.REVOKED)
        self.assertTrue(
            AuditEvent.objects.filter(object_uuid=self.indicator.uuid, action="instance_export_revoke").exists()
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.owner, message__icontains="revoked").exists()
        )

    def test_bulk_approve_preview_and_confirm(self):
        self.indicator.status = LifecycleStatus.PUBLISHED
        self.indicator.save(update_fields=["status"])
        self.client.force_login(self.reviewer)
        bulk_url = reverse("nbms_app:reporting_instance_approval_bulk", args=[self.instance.uuid])
        preview = self.client.post(
            bulk_url,
            {"obj_type": "indicators", "mode": "visible", "action": "approve"},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "Confirm bulk action")
        confirm = self.client.post(
            bulk_url,
            {"obj_type": "indicators", "mode": "visible", "action": "approve", "confirm": "1"},
        )
        self.assertEqual(confirm.status_code, 302)
        self.assertTrue(
            InstanceExportApproval.objects.filter(
                reporting_instance=self.instance,
                object_uuid=self.indicator.uuid,
                decision=ApprovalDecision.APPROVED,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(action="instance_export_bulk", object_uuid=self.instance.uuid).exists()
        )

    def test_bulk_approve_skips_missing_consent(self):
        iplc_indicator = Indicator.objects.create(
            code="IND-IPLC",
            title="IPLC Indicator",
            national_target=self.target,
            organisation=self.org_a,
            created_by=self.owner,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )
        self.client.force_login(self.reviewer)
        bulk_url = reverse("nbms_app:reporting_instance_approval_bulk", args=[self.instance.uuid])
        self.client.post(
            bulk_url,
            {
                "obj_type": "indicators",
                "mode": "selected",
                "action": "approve",
                "selected": [str(iplc_indicator.uuid)],
                "confirm": "1",
            },
        )
        self.assertFalse(
            InstanceExportApproval.objects.filter(
                reporting_instance=self.instance,
                object_uuid=iplc_indicator.uuid,
                decision=ApprovalDecision.APPROVED,
            ).exists()
        )
