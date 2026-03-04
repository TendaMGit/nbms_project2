from django.core.management.base import BaseCommand

from nbms_app.services.analytics_schema import create_analytics_views


class Command(BaseCommand):
    help = "Create analytics schema views that expose only published, export-approved indicator outputs."

    def handle(self, *args, **options):
        created = create_analytics_views()
        self.stdout.write(
            self.style.SUCCESS(
                "Ensured analytics views: " + ", ".join(created)
            )
        )
