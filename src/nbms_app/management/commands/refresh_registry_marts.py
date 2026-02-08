from __future__ import annotations

from django.core.management.base import BaseCommand

from nbms_app.services.registry_marts import refresh_registry_gold_marts


class Command(BaseCommand):
    help = "Refresh taxon/ecosystem/IAS gold summary marts for dashboards, indicators, and report products."

    def handle(self, *args, **options):
        summary = refresh_registry_gold_marts()
        self.stdout.write(
            self.style.SUCCESS(
                "Registry marts refreshed: "
                f"snapshot_date={summary['snapshot_date']} "
                f"taxon_rows={summary['taxon_rows']} "
                f"ecosystem_rows={summary['ecosystem_rows']} "
                f"ias_rows={summary['ias_rows']}"
            )
        )
