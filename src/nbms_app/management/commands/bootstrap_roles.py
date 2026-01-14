from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from nbms_app.roles import CANONICAL_GROUPS


class Command(BaseCommand):
    help = "Create canonical NBMS groups."

    def handle(self, *args, **options):
        created = 0
        for name in CANONICAL_GROUPS:
            _, was_created = Group.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Ensured {len(CANONICAL_GROUPS)} groups ({created} created)."
            )
        )
