from __future__ import annotations

import os

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import User
from nbms_app.services.authorization import ROLE_SYSTEM_ADMIN


class Command(BaseCommand):
    help = "Create/update a system admin user from NBMS_ADMIN_* environment variables."

    def handle(self, *args, **options):
        username = (os.environ.get("NBMS_ADMIN_USERNAME") or "").strip()
        email = (os.environ.get("NBMS_ADMIN_EMAIL") or "").strip()
        password = os.environ.get("NBMS_ADMIN_PASSWORD") or ""
        first_name = (os.environ.get("NBMS_ADMIN_FIRST_NAME") or "").strip()
        last_name = (os.environ.get("NBMS_ADMIN_LAST_NAME") or "").strip()

        missing = [name for name, value in [("NBMS_ADMIN_USERNAME", username), ("NBMS_ADMIN_EMAIL", email), ("NBMS_ADMIN_PASSWORD", password)] if not value]
        if missing:
            raise CommandError(
                "Missing required env vars: " + ", ".join(missing) + ". "
                "Set NBMS_ADMIN_USERNAME, NBMS_ADMIN_EMAIL and NBMS_ADMIN_PASSWORD."
            )

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        group, _ = Group.objects.get_or_create(name=ROLE_SYSTEM_ADMIN)
        user.groups.add(group)

        permission = Permission.objects.filter(
            codename="system_admin",
            content_type__app_label="nbms_app",
        ).first()
        if not permission:
            raise CommandError("Missing permission nbms_app.system_admin; run migrations first.")
        user.user_permissions.add(permission)

        groups = list(user.groups.order_by("name", "id").values_list("name", flat=True))
        perms = sorted(user.get_user_permissions())
        status = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"System admin {status}: username={user.username}, staff={user.is_staff}, superuser={user.is_superuser}"
            )
        )
        self.stdout.write(f"Groups: {', '.join(groups)}")
        self.stdout.write(f"Permissions: {', '.join(perms)}")
