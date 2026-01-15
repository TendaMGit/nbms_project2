from datetime import date

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase

from nbms_app.models import ConsentRecord, ConsentStatus, NationalTarget, Organisation, ReportingCycle, ReportingInstance, User
from nbms_app.roles import CANONICAL_GROUPS


class ConsentModelTests(TestCase):
    def test_consent_record_defaults(self):
        org = Organisation.objects.create(name="Org A")
        user = User.objects.create_user(username="owner", password="pass1234", organisation=org)
        cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        instance = ReportingInstance.objects.create(cycle=cycle)
        target = NationalTarget.objects.create(code="NT1", title="Target", organisation=org, created_by=user)
        record = ConsentRecord.objects.create(
            content_type=ContentType.objects.get_for_model(NationalTarget),
            object_uuid=target.uuid,
            reporting_instance=instance,
        )
        self.assertEqual(record.status, ConsentStatus.REQUIRED)

    def test_community_rep_role_exists(self):
        call_command("bootstrap_roles")
        self.assertIn("Community Representative", CANONICAL_GROUPS)
        self.assertTrue(Group.objects.filter(name="Community Representative").exists())
