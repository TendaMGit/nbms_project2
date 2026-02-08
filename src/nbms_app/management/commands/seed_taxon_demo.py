from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed demo taxon backbone rows and specimen vouchers."

    def handle(self, *args, **options):
        call_command("sync_taxon_backbone", "--seed-demo", "--skip-remote")
        call_command("sync_specimen_vouchers", "--seed-demo")
        self.stdout.write(self.style.SUCCESS("Seeded taxon demo registry rows."))
