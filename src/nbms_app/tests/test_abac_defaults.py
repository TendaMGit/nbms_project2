from django.test import TestCase

from nbms_app.models import Indicator, LifecycleStatus, NationalTarget, SensitivityLevel


class AbacDefaultsTests(TestCase):
    def test_national_target_defaults(self):
        target = NationalTarget.objects.create(code="NT1", title="Target 1")
        self.assertIsNotNone(target.uuid)
        self.assertEqual(target.status, LifecycleStatus.DRAFT)
        self.assertEqual(target.sensitivity, SensitivityLevel.INTERNAL)
        self.assertIsNone(target.created_by)
        self.assertIsNone(target.organisation)

    def test_indicator_defaults(self):
        target = NationalTarget.objects.create(code="NT2", title="Target 2")
        indicator = Indicator.objects.create(code="IND1", title="Indicator 1", national_target=target)
        self.assertIsNotNone(indicator.uuid)
        self.assertEqual(indicator.status, LifecycleStatus.DRAFT)
        self.assertEqual(indicator.sensitivity, SensitivityLevel.INTERNAL)
        self.assertIsNone(indicator.created_by)
        self.assertIsNone(indicator.organisation)
