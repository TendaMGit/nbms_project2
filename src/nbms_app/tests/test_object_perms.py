from django.contrib.auth.models import Group
from django.test import TestCase

from nbms_app.models import LifecycleStatus, NationalTarget, Organisation, SensitivityLevel, User
from nbms_app.services.authorization import ROLE_SECRETARIAT, filter_queryset_for_user


class ObjectPermissionTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.creator = User.objects.create_user(
            username="creator",
            password="pass1234",
            organisation=self.org,
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            password="pass1234",
            organisation=self.org,
        )
        self.secretariat = User.objects.create_user(
            username="secretariat",
            password="pass1234",
            organisation=self.org,
        )
        self.secretariat_group = Group.objects.create(name=ROLE_SECRETARIAT)
        self.secretariat.groups.add(self.secretariat_group)

    def test_creator_gets_object_perms(self):
        target = NationalTarget.objects.create(
            code="NT1",
            title="Target",
            organisation=self.org,
            created_by=self.creator,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        self.assertTrue(self.creator.has_perm("nbms_app.view_nationaltarget", target))
        self.assertTrue(self.creator.has_perm("nbms_app.change_nationaltarget", target))

    def test_secretariat_group_gets_perms(self):
        target = NationalTarget.objects.create(
            code="NT2",
            title="Target 2",
            organisation=self.org,
            created_by=self.creator,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        self.assertTrue(self.secretariat.has_perm("nbms_app.view_nationaltarget", target))
        self.assertTrue(self.secretariat.has_perm("nbms_app.change_nationaltarget", target))

    def test_filter_queryset_requires_object_perm_for_non_public(self):
        target = NationalTarget.objects.create(
            code="NT3",
            title="Target 3",
            organisation=self.org,
            created_by=self.creator,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        qs = NationalTarget.objects.all()
        viewer_visible = filter_queryset_for_user(qs, self.viewer, perm="nbms_app.view_nationaltarget")
        creator_visible = filter_queryset_for_user(qs, self.creator, perm="nbms_app.view_nationaltarget")
        self.assertNotIn(target, viewer_visible)
        self.assertIn(target, creator_visible)
