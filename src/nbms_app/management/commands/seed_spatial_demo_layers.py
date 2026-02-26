from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backward-compatible alias for seed_demo_spatial."

    def handle(self, *args, **options):
        call_command("seed_demo_spatial")
