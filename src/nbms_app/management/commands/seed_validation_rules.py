import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nbms_app.models import ValidationRuleSet, ValidationScope


DEFAULT_RULES = {
    "sections": {
        "required": ["I", "II", "III", "IV", "V"],
        "completion": {
            "missing_if_empty": True,
            "draft_if_any_content": True,
            "completed_if_nonempty": True,
        },
    },
    "indicator": {
        "required_fields": ["title", "code", "organisation", "status"],
        "recommended_fields": ["review_note"],
        "requires_links": {"national_targets_min": 1},
    },
    "national_target": {
        "required_fields": ["code", "title", "organisation", "status"],
    },
    "evidence": {
        "required_fields": ["title", "evidence_type", "organisation", "status"],
    },
    "dataset": {
        "required_fields": ["title", "methodology", "organisation", "status"],
        "requires_release_for_export": True,
    },
}


def _validate_rules(rules):
    if not isinstance(rules, dict):
        raise CommandError("rules_json must be a dict.")
    sections = rules.get("sections")
    if sections is not None:
        if not isinstance(sections, dict):
            raise CommandError("rules_json.sections must be a dict.")
        required = sections.get("required", [])
        if required is not None and not isinstance(required, list):
            raise CommandError("rules_json.sections.required must be a list.")
        completion = sections.get("completion", {})
        if completion is not None and not isinstance(completion, dict):
            raise CommandError("rules_json.sections.completion must be a dict.")
    for key in ("indicator", "national_target", "evidence", "dataset"):
        payload = rules.get(key)
        if payload is None:
            continue
        if not isinstance(payload, dict):
            raise CommandError(f"rules_json.{key} must be a dict.")
        required_fields = payload.get("required_fields")
        if required_fields is not None and not isinstance(required_fields, list):
            raise CommandError(f"rules_json.{key}.required_fields must be a list.")
    try:
        json.dumps(rules)
    except TypeError as exc:
        raise CommandError(f"rules_json must be JSON-serializable: {exc}") from exc


class Command(BaseCommand):
    help = "Seed the default ValidationRuleSet for 7NR reporting."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-existing-active",
            action="store_true",
            dest="keep_existing_active",
            help="Do not deactivate existing active rule sets.",
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            dest="activate",
            help="Activate 7NR_DEFAULT even when keeping existing active rule sets.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show changes without writing to the database.",
        )

    def handle(self, *args, **options):
        keep_existing_active = options["keep_existing_active"]
        activate = options["activate"]
        dry_run = options["dry_run"]
        _validate_rules(DEFAULT_RULES)

        changes = []
        existing = ValidationRuleSet.objects.filter(code="7NR_DEFAULT").first()
        desired_active = True
        if keep_existing_active:
            if existing:
                desired_active = True if activate else existing.is_active
            else:
                desired_active = activate

        if existing:
            if existing.rules_json != DEFAULT_RULES:
                changes.append("update rules_json for 7NR_DEFAULT")
                existing.rules_json = DEFAULT_RULES
            if existing.applies_to != ValidationScope.REPORT_TYPE:
                changes.append("update applies_to for 7NR_DEFAULT")
                existing.applies_to = ValidationScope.REPORT_TYPE
            if existing.is_active != desired_active:
                changes.append(
                    f"set 7NR_DEFAULT is_active={desired_active}"
                    if keep_existing_active
                    else "activate 7NR_DEFAULT"
                )
                existing.is_active = desired_active
        else:
            changes.append("create 7NR_DEFAULT")

        deactivate_count = 0
        if not keep_existing_active:
            deactivate_count = (
                ValidationRuleSet.objects.filter(is_active=True)
                .exclude(code="7NR_DEFAULT")
                .count()
            )
            if deactivate_count:
                changes.append(f"deactivate {deactivate_count} existing rule set(s)")

        if dry_run:
            if changes:
                for change in changes:
                    self.stdout.write(self.style.WARNING(f"[dry-run] {change}"))
            else:
                self.stdout.write(self.style.SUCCESS("[dry-run] No changes needed."))
            return

        with transaction.atomic():
            if existing:
                if changes:
                    existing.save()
                    self.stdout.write(self.style.SUCCESS("Updated 7NR_DEFAULT ruleset."))
                else:
                    self.stdout.write(self.style.SUCCESS("7NR_DEFAULT already up to date."))
            else:
                ValidationRuleSet.objects.create(
                    code="7NR_DEFAULT",
                    applies_to=ValidationScope.REPORT_TYPE,
                    rules_json=DEFAULT_RULES,
                    is_active=desired_active,
                )
                self.stdout.write(self.style.SUCCESS("Created 7NR_DEFAULT ruleset."))

            if not keep_existing_active and deactivate_count:
                ValidationRuleSet.objects.filter(is_active=True).exclude(code="7NR_DEFAULT").update(is_active=False)
                self.stdout.write(self.style.SUCCESS("Deactivated existing active rule sets."))
