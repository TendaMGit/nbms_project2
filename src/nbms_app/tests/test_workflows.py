from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from nbms_app.models import Indicator, LifecycleStatus, NationalTarget, Organisation, User
from nbms_app.services.authorization import ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD, ROLE_SECRETARIAT
from nbms_app.services.workflows import approve, archive, publish, reject, submit_for_review


class WorkflowTransitionTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.owner = User.objects.create_user(
            username="owner",
            password="pass1234",
            organisation=self.org,
        )
        self.indicator_lead = User.objects.create_user(
            username="lead",
            password="pass1234",
            organisation=self.org,
        )
        self.indicator_lead.groups.create(name=ROLE_INDICATOR_LEAD)
        self.data_steward = User.objects.create_user(
            username="steward",
            password="pass1234",
            organisation=self.org,
        )
        self.data_steward.groups.create(name=ROLE_DATA_STEWARD)
        self.secretariat = User.objects.create_user(
            username="secretariat",
            password="pass1234",
            organisation=self.org,
        )
        self.secretariat.groups.create(name=ROLE_SECRETARIAT)

        self.target = NationalTarget.objects.create(
            code="NT-1",
            title="Target",
            organisation=self.org,
            created_by=self.owner,
        )
        self.indicator = Indicator.objects.create(
            code="IND-1",
            title="Indicator",
            national_target=self.target,
            organisation=self.org,
            created_by=self.owner,
        )

    def test_submit_for_review_owner_allowed(self):
        submit_for_review(self.target, self.owner)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, LifecycleStatus.PENDING_REVIEW)

    def test_submit_for_review_indicator_lead_allowed(self):
        submit_for_review(self.indicator, self.indicator_lead)
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.status, LifecycleStatus.PENDING_REVIEW)

    def test_submit_for_review_blocked_for_random_user(self):
        random_user = User.objects.create_user(username="random", password="pass1234")
        with self.assertRaises(PermissionDenied):
            submit_for_review(self.target, random_user)

    def test_approve_requires_reviewer(self):
        submit_for_review(self.target, self.owner)
        with self.assertRaises(PermissionDenied):
            approve(self.target, self.owner, note="ok")
        approve(self.target, self.data_steward, note="ok")
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, LifecycleStatus.APPROVED)

    def test_reject_requires_note(self):
        submit_for_review(self.indicator, self.owner)
        with self.assertRaises(ValidationError):
            reject(self.indicator, self.data_steward, note="")
        reject(self.indicator, self.data_steward, note="needs work")
        self.indicator.refresh_from_db()
        self.assertEqual(self.indicator.status, LifecycleStatus.DRAFT)
        self.assertEqual(self.indicator.review_note, "needs work")

    def test_publish_archive_roles(self):
        submit_for_review(self.target, self.owner)
        approve(self.target, self.data_steward, note="ok")
        with self.assertRaises(PermissionDenied):
            publish(self.target, self.data_steward)
        publish(self.target, self.secretariat)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, LifecycleStatus.PUBLISHED)
        archive(self.target, self.secretariat)
        self.target.refresh_from_db()
        self.assertEqual(self.target.status, LifecycleStatus.ARCHIVED)

    def test_publish_requires_approved(self):
        with self.assertRaises(ValidationError):
            publish(self.indicator, self.secretariat)
