from django.contrib.auth.models import Group
from django.test import TestCase

from nbms_app.models import AuditEvent, Dataset, DatasetRelease, Evidence, LifecycleStatus, Notification, Organisation, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD, ROLE_SECRETARIAT
from nbms_app.services.workflows import approve, publish, submit_for_review


class DomainWorkflowTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.owner = User.objects.create_user(
            username="owner",
            password="pass1234",
            organisation=self.org,
        )
        self.data_steward = User.objects.create_user(
            username="steward",
            password="pass1234",
            organisation=self.org,
        )
        self.data_steward.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.secretariat = User.objects.create_user(
            username="secretariat",
            password="pass1234",
            organisation=self.org,
        )
        self.secretariat.groups.add(Group.objects.create(name=ROLE_SECRETARIAT))

    def test_evidence_workflow_creates_audit_and_notifications(self):
        evidence = Evidence.objects.create(
            title="Evidence A",
            organisation=self.org,
            created_by=self.owner,
        )

        submit_for_review(evidence, self.owner)
        approve(evidence, self.data_steward, note="ok")
        publish(evidence, self.secretariat)

        evidence.refresh_from_db()
        self.assertEqual(evidence.status, LifecycleStatus.PUBLISHED)

        actions = set(
            AuditEvent.objects.filter(object_uuid=evidence.uuid).values_list("action", flat=True)
        )
        self.assertIn("submit_for_review", actions)
        self.assertIn("approve", actions)
        self.assertIn("publish", actions)

        notifications = Notification.objects.filter(recipient=self.owner)
        self.assertGreaterEqual(notifications.count(), 3)

    def test_dataset_release_workflow_creates_audit_and_notifications(self):
        dataset = Dataset.objects.create(
            title="Dataset A",
            organisation=self.org,
            created_by=self.owner,
        )
        release = DatasetRelease.objects.create(
            dataset=dataset,
            version="v1",
            snapshot_title="Dataset A",
            snapshot_description="",
            snapshot_methodology="",
            organisation=self.org,
            created_by=self.owner,
        )

        submit_for_review(release, self.owner)
        approve(release, self.data_steward, note="ok")
        publish(release, self.secretariat)

        release.refresh_from_db()
        self.assertEqual(release.status, LifecycleStatus.PUBLISHED)

        actions = set(
            AuditEvent.objects.filter(object_uuid=release.uuid).values_list("action", flat=True)
        )
        self.assertIn("submit_for_review", actions)
        self.assertIn("approve", actions)
        self.assertIn("publish", actions)

        notifications = Notification.objects.filter(recipient=self.owner)
        self.assertGreaterEqual(notifications.count(), 3)
