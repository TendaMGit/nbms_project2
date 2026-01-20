from django.core.management import call_command
from django.test import TestCase

from nbms_app.models import ReportSectionTemplate, ValidationRuleSet, ValidationScope


class Nr7TemplateAuditTests(TestCase):
    def test_nr7_templates_exist_and_seed_idempotent(self):
        self.assertEqual(ReportSectionTemplate.objects.count(), 0)
        call_command("seed_report_templates")
        self.assertEqual(
            ReportSectionTemplate.objects.filter(
                code__in=[
                    "section-i",
                    "section-ii",
                    "section-iii",
                    "section-iv",
                    "section-v",
                    "section-other-information",
                ]
            ).count(),
            6,
        )
        call_command("seed_report_templates")
        self.assertEqual(ReportSectionTemplate.objects.count(), 6)

    def test_readiness_ruleset_references_templates(self):
        call_command("seed_report_templates")
        call_command("seed_validation_rules")
        call_command("audit_nr7_templates")

    def test_audit_fails_when_template_missing(self):
        call_command("seed_report_templates")
        ReportSectionTemplate.objects.filter(code="section-iv").delete()
        call_command("seed_validation_rules")
        with self.assertRaises(Exception):
            call_command("audit_nr7_templates")

    def test_audit_fails_when_ruleset_missing_required_sections(self):
        call_command("seed_report_templates")
        ValidationRuleSet.objects.create(
            code="7NR_DEFAULT",
            applies_to=ValidationScope.REPORT_TYPE,
            rules_json={"sections": {"required": ["I", "II", "III", "IV"]}},
            is_active=True,
        )
        with self.assertRaises(Exception):
            call_command("audit_nr7_templates")
