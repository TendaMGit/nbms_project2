from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import ReportSectionTemplate, ValidationRuleSet


REQUIRED_TEMPLATE_CODES = (
    "section-i",
    "section-ii",
    "section-iii",
    "section-iv",
    "section-v",
    "section-other-information",
)


class Command(BaseCommand):
    help = "Audit NR7 report section templates and readiness rules."

    def handle(self, *args, **options):
        templates = ReportSectionTemplate.objects.filter(code__in=REQUIRED_TEMPLATE_CODES)
        template_map = {template.code: template for template in templates}
        missing = [code for code in REQUIRED_TEMPLATE_CODES if code not in template_map]
        inactive = [code for code, template in template_map.items() if not template.is_active]

        ruleset = ValidationRuleSet.objects.filter(code="7NR_DEFAULT", is_active=True).first()
        required_codes = []
        if ruleset:
            required_codes = (ruleset.rules_json or {}).get("sections", {}).get("required", []) or []
        normalized_required = {_normalize_section_code(code) for code in required_codes}
        missing_in_rules = [
            code for code in REQUIRED_TEMPLATE_CODES if code != "section-other-information" and code not in normalized_required
        ]

        if missing or inactive or missing_in_rules or not ruleset:
            if missing:
                self.stderr.write(self.style.ERROR(f"Missing templates: {', '.join(missing)}"))
            if inactive:
                self.stderr.write(self.style.ERROR(f"Inactive templates: {', '.join(inactive)}"))
            if not ruleset:
                self.stderr.write(self.style.ERROR("Missing active 7NR_DEFAULT ValidationRuleSet."))
            if missing_in_rules:
                self.stderr.write(
                    self.style.ERROR(
                        "7NR_DEFAULT ruleset missing required section codes: "
                        + ", ".join(sorted(missing_in_rules))
                    )
                )
            raise CommandError("NR7 template audit failed.")

        self.stdout.write(self.style.SUCCESS("NR7 template audit passed."))


def _normalize_section_code(code):
    if not code:
        return ""
    trimmed = str(code).strip().lower()
    if trimmed.startswith("section-"):
        return trimmed
    roman_map = {
        "i": "section-i",
        "ii": "section-ii",
        "iii": "section-iii",
        "iv": "section-iv",
        "v": "section-v",
        "1": "section-i",
        "2": "section-ii",
        "3": "section-iii",
        "4": "section-iv",
        "5": "section-v",
    }
    return roman_map.get(trimmed, trimmed)
