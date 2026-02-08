from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed minimal VegMap demo extraction using existing open spatial baseline layers."

    def handle(self, *args, **options):
        call_command("sync_spatial_sources", "--source-code", "NE_GEOREGIONS_ZA")
        call_command("sync_vegmap_baseline", "--use-demo-layer", "--vegmap-version", "demo")
        self.stdout.write(self.style.SUCCESS("Seeded VegMap demo registry rows."))
