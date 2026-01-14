from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from nbms_app.forms import UserCreateForm
from nbms_app.roles import CANONICAL_GROUPS


class RolesBootstrapTests(TestCase):
    def test_bootstrap_creates_groups(self):
        call_command("bootstrap_roles")
        for name in CANONICAL_GROUPS:
            self.assertTrue(Group.objects.filter(name=name).exists())

    def test_user_form_limits_groups(self):
        Group.objects.create(name="Other")
        call_command("bootstrap_roles")
        form = UserCreateForm()
        names = list(form.fields["groups"].queryset.values_list("name", flat=True))
        self.assertIn(CANONICAL_GROUPS[0], names)
        self.assertNotIn("Other", names)
