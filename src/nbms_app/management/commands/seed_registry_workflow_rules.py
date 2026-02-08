from __future__ import annotations

from django.core.management.base import BaseCommand

from nbms_app.models import ValidationRuleSet, ValidationScope


DEFAULT_RULES = {
    "evidence_required_for_actions": {
        "ecosystem_crosswalk": ["approve", "publish"],
        "ecosystem_risk_assessment": ["approve", "publish"],
        "eicat_assessment": ["approve", "publish"],
        "seicat_assessment": ["approve", "publish"],
    }
}


class Command(BaseCommand):
    help = "Seed default validation rules controlling registry workflow evidence gates."

    def handle(self, *args, **options):
        row, created = ValidationRuleSet.objects.update_or_create(
            code="REGISTRY_WORKFLOW_DEFAULT",
            defaults={
                "applies_to": ValidationScope.REPORT_TYPE,
                "rules_json": DEFAULT_RULES,
                "is_active": True,
            },
        )
        state = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"{state} rule set {row.code}"))
