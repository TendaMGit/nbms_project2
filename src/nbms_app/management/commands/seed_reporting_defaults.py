from django.core.management import call_command
from django.core.management.base import BaseCommand

from nbms_app.models import ReportSectionTemplate, ValidationRuleSet


class Command(BaseCommand):
    help = "Seed reporting section templates and validation rules."

    def handle(self, *args, **options):
        self.stdout.write("Seeding report section templates...")
        call_command("seed_report_templates")
        self.stdout.write("Seeding MEA template packs...")
        call_command("seed_mea_template_packs")
        self.stdout.write("Seeding validation rules...")
        call_command("seed_validation_rules")
        self.stdout.write(
            self.style.SUCCESS(
                f"Reporting defaults seeded: {ReportSectionTemplate.objects.count()} templates, "
                f"{ValidationRuleSet.objects.count()} ruleset(s)."
            )
        )
