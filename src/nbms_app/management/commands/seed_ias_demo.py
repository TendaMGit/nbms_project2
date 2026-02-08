from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed demo IAS baseline rows with EICAT/SEICAT placeholders."

    def handle(self, *args, **options):
        call_command("sync_griis_za", "--seed-demo")
        self.stdout.write(self.style.SUCCESS("Seeded IAS demo registry rows."))
