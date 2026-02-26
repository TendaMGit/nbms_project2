from django.core.management.base import BaseCommand

from nbms_app.integrations.birdie.service import ingest_birdie_snapshot


class Command(BaseCommand):
    help = "Seed and ingest BIRDIE integration snapshot into bronze/silver/gold layers."

    def handle(self, *args, **options):
        summary = ingest_birdie_snapshot(actor=None)
        self.stdout.write(
            self.style.SUCCESS(
                "BIRDIE ingest complete: "
                f"species={summary['species_count']}, "
                f"sites={summary['site_count']}, "
                f"abundance={summary['abundance_row_count']}, "
                f"occupancy={summary['occupancy_row_count']}, "
                f"wcv={summary['wcv_row_count']}"
            )
        )
