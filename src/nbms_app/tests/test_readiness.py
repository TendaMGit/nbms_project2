from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from nbms_app.models import (
    ConsentStatus,
    Dataset,
    DatasetRelease,
    Evidence,
    ExportPackage,
    ExportStatus,
    Indicator,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportSectionResponse,
    ReportSectionTemplate,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
    ValidationRuleSet,
    ValidationScope,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD
from nbms_app.services.consent import set_consent_status
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.readiness import (
    get_dataset_readiness,
    get_evidence_readiness,
    get_export_package_readiness,
    get_indicator_readiness,
    get_instance_readiness,
    get_target_readiness,
)


class ReadinessTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.staff = User.objects.create_user(
            username="staff",
            password="pass1234",
            organisation=self.org,
            is_staff=True,
        )
        self.reviewer = User.objects.create_user(
            username="reviewer",
            password="pass1234",
            organisation=self.org,
        )
        self.reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

    @override_settings(EXPORT_REQUIRE_SECTIONS=True)
    def test_instance_readiness_blocker_and_ok(self):
        ReportSectionTemplate.objects.create(
            code="section-i",
            title="Section I",
            ordering=1,
            schema_json={"required": True, "fields": [{"key": "summary"}]},
        )
        target = NationalTarget.objects.create(
            code="NT-1",
            title="Target 1",
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.IPLC_SENSITIVE,
        )
        approve_for_instance(self.instance, target, self.staff, admin_override=True)
        readiness = get_instance_readiness(self.instance, self.staff)
        self.assertFalse(readiness["ok"])
        self.assertEqual(readiness["status"], "red")
        self.assertTrue(readiness["blockers"])
        self.assertIn("readiness_score", readiness)
        self.assertTrue(readiness["top_10_actions"])
        self.assertEqual(readiness["top_10_actions"][0]["title"], "Missing required sections")

        ReportSectionResponse.objects.create(
            reporting_instance=self.instance,
            template=ReportSectionTemplate.objects.get(code="section-i"),
            response_json={"summary": "Done"},
            updated_by=self.staff,
        )
        set_consent_status(self.instance, target, self.staff, ConsentStatus.GRANTED)
        readiness = get_instance_readiness(self.instance, self.staff)
        self.assertTrue(readiness["ok"])
        self.assertEqual(readiness["status"], "green")
        self.assertGreaterEqual(readiness["readiness_score"], 50)

    def test_instance_readiness_abac_counts(self):
        other_org = Organisation.objects.create(name="Org B")
        other_user = User.objects.create_user(
            username="other",
            password="pass1234",
            organisation=other_org,
        )
        target = NationalTarget.objects.create(
            code="NT-OTHER",
            title="Target Other",
            organisation=other_org,
            created_by=other_user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.INTERNAL,
        )
        approve_for_instance(self.instance, target, self.staff, admin_override=True)
        readiness = get_instance_readiness(self.instance, self.reviewer)
        self.assertEqual(readiness["details"]["approvals"]["targets"]["total"], 0)

    def test_indicator_readiness_blocker_and_ok(self):
        target = NationalTarget.objects.create(
            code="NT-2",
            title="Target 2",
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        indicator = Indicator.objects.create(
            code="IND-1",
            title="Indicator 1",
            national_target=target,
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        readiness = get_indicator_readiness(indicator, self.staff, instance=self.instance)
        self.assertFalse(readiness["ok"])

        indicator.status = LifecycleStatus.PUBLISHED
        indicator.save(update_fields=["status"])
        approve_for_instance(self.instance, indicator, self.staff)
        readiness = get_indicator_readiness(indicator, self.staff, instance=self.instance)
        self.assertTrue(readiness["ok"])
        self.assertEqual(readiness["status"], "amber")

    def test_target_readiness_blocker_and_ok(self):
        target = NationalTarget.objects.create(
            code="NT-3",
            title="Target 3",
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        readiness = get_target_readiness(target, self.staff, instance=self.instance)
        self.assertFalse(readiness["ok"])

        target.status = LifecycleStatus.PUBLISHED
        target.save(update_fields=["status"])
        approve_for_instance(self.instance, target, self.staff)
        readiness = get_target_readiness(target, self.staff, instance=self.instance)
        self.assertTrue(readiness["ok"])
        self.assertEqual(readiness["status"], "amber")

    def test_evidence_readiness_blocker_and_ok(self):
        evidence = Evidence.objects.create(
            title="Evidence 1",
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        readiness = get_evidence_readiness(evidence, self.staff, instance=self.instance)
        self.assertFalse(readiness["ok"])

        evidence.status = LifecycleStatus.PUBLISHED
        evidence.save(update_fields=["status"])
        approve_for_instance(self.instance, evidence, self.staff)
        readiness = get_evidence_readiness(evidence, self.staff, instance=self.instance)
        self.assertTrue(readiness["ok"])
        self.assertEqual(readiness["status"], "amber")

    def test_dataset_readiness_blocker_and_ok(self):
        dataset = Dataset.objects.create(
            title="Dataset 1",
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.DRAFT,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        readiness = get_dataset_readiness(dataset, self.staff, instance=self.instance)
        self.assertFalse(readiness["ok"])

        dataset.status = LifecycleStatus.PUBLISHED
        dataset.save(update_fields=["status"])
        DatasetRelease.objects.create(
            dataset=dataset,
            version="v1",
            snapshot_title="Dataset 1",
            snapshot_description="",
            snapshot_methodology="",
            organisation=self.org,
            created_by=self.reviewer,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        approve_for_instance(self.instance, dataset, self.staff)
        readiness = get_dataset_readiness(dataset, self.staff, instance=self.instance)
        self.assertTrue(readiness["ok"])
        self.assertEqual(readiness["status"], "amber")

    def test_export_package_readiness_blocker_and_ok(self):
        ReportSectionTemplate.objects.create(
            code="section-x",
            title="Section X",
            ordering=1,
            schema_json={"required": False, "fields": [{"key": "summary"}]},
        )
        package = ExportPackage.objects.create(
            title="Export A",
            organisation=self.org,
            created_by=self.reviewer,
            reporting_instance=self.instance,
            status=ExportStatus.DRAFT,
        )
        readiness = get_export_package_readiness(package, self.staff)
        self.assertFalse(readiness["ok"])

        package.status = ExportStatus.APPROVED
        package.save(update_fields=["status"])
        readiness = get_export_package_readiness(package, self.staff)
        self.assertTrue(readiness["ok"])
        self.assertEqual(readiness["status"], "amber")

    @override_settings(EXPORT_REQUIRE_SECTIONS=True)
    def test_validation_rule_set_overrides_required_sections(self):
        ValidationRuleSet.objects.create(
            code="7NR_DEFAULT",
            applies_to=ValidationScope.REPORT_TYPE,
            rules_json={"sections": {"required": ["I"]}},
        )
        ReportSectionTemplate.objects.create(
            code="section-i",
            title="Section I",
            ordering=1,
            schema_json={"required": False, "fields": [{"key": "summary"}]},
        )
        readiness = get_instance_readiness(self.instance, self.staff)
        self.assertFalse(readiness["ok"])
        self.assertTrue(readiness["blockers"])
