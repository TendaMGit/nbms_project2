from django.core.management.base import BaseCommand

from nbms_app.services.report_products import seed_default_report_products


class Command(BaseCommand):
    help = "Seed default One Biodiversity report product templates."

    def handle(self, *args, **options):
        templates = seed_default_report_products()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded report products: {', '.join(item.code for item in templates)}"
            )
        )
