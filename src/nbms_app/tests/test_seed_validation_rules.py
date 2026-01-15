from django.core.management import call_command
from django.test import TestCase

from nbms_app.models import ValidationRuleSet, ValidationScope


class SeedValidationRulesTests(TestCase):
    def test_creates_default_ruleset(self):
        call_command("seed_validation_rules")

        ruleset = ValidationRuleSet.objects.get(code="7NR_DEFAULT")
        self.assertTrue(ruleset.is_active)
        self.assertEqual(ruleset.applies_to, ValidationScope.REPORT_TYPE)
        self.assertIn("sections", ruleset.rules_json)

    def test_updates_existing_and_deactivates_others(self):
        ValidationRuleSet.objects.create(
            code="OTHER",
            applies_to=ValidationScope.REPORT_TYPE,
            rules_json={"sections": {"required": ["I"]}},
            is_active=True,
        )
        ValidationRuleSet.objects.create(
            code="7NR_DEFAULT",
            applies_to=ValidationScope.CYCLE,
            rules_json={"sections": {"required": ["II"]}},
            is_active=False,
        )

        call_command("seed_validation_rules")
        ruleset = ValidationRuleSet.objects.get(code="7NR_DEFAULT")
        other = ValidationRuleSet.objects.get(code="OTHER")
        self.assertTrue(ruleset.is_active)
        self.assertEqual(ruleset.applies_to, ValidationScope.REPORT_TYPE)
        self.assertIn("sections", ruleset.rules_json)
        self.assertFalse(other.is_active)

        call_command("seed_validation_rules")
        self.assertEqual(ValidationRuleSet.objects.count(), 2)

    def test_keep_existing_active_preserves_active(self):
        ValidationRuleSet.objects.create(
            code="OTHER",
            applies_to=ValidationScope.REPORT_TYPE,
            rules_json={"sections": {"required": ["I"]}},
            is_active=True,
        )
        ValidationRuleSet.objects.create(
            code="7NR_DEFAULT",
            applies_to=ValidationScope.REPORT_TYPE,
            rules_json={"sections": {"required": ["II"]}},
            is_active=False,
        )

        call_command("seed_validation_rules", keep_existing_active=True)
        ruleset = ValidationRuleSet.objects.get(code="7NR_DEFAULT")
        other = ValidationRuleSet.objects.get(code="OTHER")
        self.assertFalse(ruleset.is_active)
        self.assertTrue(other.is_active)

        call_command("seed_validation_rules", keep_existing_active=True, activate=True)
        ruleset.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(ruleset.is_active)
        self.assertTrue(other.is_active)

    def test_dry_run_makes_no_changes(self):
        call_command("seed_validation_rules", dry_run=True)
        self.assertEqual(ValidationRuleSet.objects.count(), 0)
