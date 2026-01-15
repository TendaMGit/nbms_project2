from django.contrib.auth.models import Group
from django.test import TestCase

from nbms_app.models import Indicator, LifecycleStatus, NationalTarget, Organisation, SensitivityLevel, User
from nbms_app.services.authorization import (
    ROLE_COMMUNITY_REPRESENTATIVE,
    ROLE_SECURITY_OFFICER,
    ROLE_SECRETARIAT,
    can_edit_object,
    can_view_object,
    filter_queryset_for_user,
)


class AuthorizationServiceTests(TestCase):
    def setUp(self):
        self.org_a = Organisation.objects.create(name="Org A")
        self.org_b = Organisation.objects.create(name="Org B")

        self.user_a = User.objects.create_user(
            username="user-a",
            password="pass1234",
            organisation=self.org_a,
        )
        self.user_b = User.objects.create_user(
            username="user-b",
            password="pass1234",
            organisation=self.org_b,
        )

        self.security_officer = User.objects.create_user(
            username="sec",
            password="pass1234",
            organisation=self.org_b,
        )
        self.security_officer.groups.add(Group.objects.create(name=ROLE_SECURITY_OFFICER))

        self.secretariat = User.objects.create_user(
            username="secretariat",
            password="pass1234",
            organisation=self.org_a,
        )
        self.secretariat.groups.add(Group.objects.create(name=ROLE_SECRETARIAT))

        self.community_rep = User.objects.create_user(
            username="community",
            password="pass1234",
            organisation=self.org_a,
        )
        self.community_rep.groups.add(Group.objects.create(name=ROLE_COMMUNITY_REPRESENTATIVE))

        self.target_public = NationalTarget.objects.create(
            code="NT-PUB",
            title="Public",
            organisation=self.org_a,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.target_internal = NationalTarget.objects.create(
            code="NT-INT",
            title="Internal",
            organisation=self.org_a,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        self.target_restricted = NationalTarget.objects.create(
            code="NT-RES",
            title="Restricted",
            organisation=self.org_b,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.RESTRICTED,
        )
        self.target_iplc = NationalTarget.objects.create(
            code="NT-IPLC",
            title="IPLC",
            organisation=self.org_a,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )
        self.target_draft = NationalTarget.objects.create(
            code="NT-DRAFT",
            title="Draft",
            organisation=self.org_a,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.INTERNAL,
            created_by=self.user_a,
        )

    def test_anonymous_can_only_view_public_published(self):
        self.assertTrue(can_view_object(None, self.target_public))
        self.assertFalse(can_view_object(None, self.target_internal))

    def test_user_cannot_view_other_org_internal(self):
        self.assertFalse(can_view_object(self.user_b, self.target_internal))

    def test_user_can_view_own_org_internal_published(self):
        self.assertTrue(can_view_object(self.user_a, self.target_internal))

    def test_security_officer_can_view_restricted_and_iplc(self):
        self.assertTrue(can_view_object(self.security_officer, self.target_restricted))
        self.assertTrue(can_view_object(self.security_officer, self.target_iplc))

    def test_creator_can_view_own_draft(self):
        self.assertTrue(can_view_object(self.user_a, self.target_draft))

    def test_secretariat_can_view_org_draft(self):
        self.assertTrue(can_view_object(self.secretariat, self.target_draft))

    def test_community_rep_can_view_iplc_published(self):
        self.assertTrue(can_view_object(self.community_rep, self.target_iplc))

    def test_can_edit_object(self):
        self.assertTrue(can_edit_object(self.secretariat, self.target_internal))
        self.assertTrue(can_edit_object(self.user_a, self.target_draft))
        self.assertFalse(can_edit_object(self.user_b, self.target_internal))

    def test_filter_queryset_for_user(self):
        qs = NationalTarget.objects.all()
        visible_for_user_a = filter_queryset_for_user(qs, self.user_a)
        self.assertIn(self.target_public, visible_for_user_a)
        self.assertIn(self.target_internal, visible_for_user_a)
        self.assertIn(self.target_draft, visible_for_user_a)
        self.assertNotIn(self.target_restricted, visible_for_user_a)

    def test_filter_queryset_for_anonymous(self):
        qs = NationalTarget.objects.all()
        visible_for_anonymous = filter_queryset_for_user(qs, None)
        self.assertIn(self.target_public, visible_for_anonymous)
        self.assertNotIn(self.target_internal, visible_for_anonymous)
