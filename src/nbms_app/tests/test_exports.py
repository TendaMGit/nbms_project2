from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Evidence,
    ExportPackage,
    ExportStatus,
    Indicator,
    LifecycleStatus,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_DATA_STEWARD, ROLE_SECRETARIAT
from nbms_app.services.exports import approve_export, build_export_payload, release_export, submit_export_for_review
from nbms_app.services.instance_approvals import approve_for_instance


class ExportPayloadTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.user = User.objects.create_user(username="owner", password="pass1234", organisation=self.org)
        self.user.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-1",
            title="Cycle 1",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

        self.target_ok = NationalTarget.objects.create(
            code="NT-OK",
            title="Target OK",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.target_hidden = NationalTarget.objects.create(
            code="NT-HIDDEN",
            title="Target Hidden",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

        self.indicator_ok = Indicator.objects.create(
            code="IND-OK",
            title="Indicator OK",
            national_target=self.target_ok,
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

        self.evidence_ok = Evidence.objects.create(
            title="Evidence OK",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.dataset_ok = Dataset.objects.create(
            title="Dataset OK",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        self.release_ok = DatasetRelease.objects.create(
            dataset=self.dataset_ok,
            version="v1",
            snapshot_title="Dataset OK",
            snapshot_description="",
            snapshot_methodology="",
            organisation=self.org,
            created_by=self.user,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )

        approve_for_instance(self.instance, self.target_ok, self.user)
        approve_for_instance(self.instance, self.indicator_ok, self.user)
        approve_for_instance(self.instance, self.evidence_ok, self.user)
        approve_for_instance(self.instance, self.dataset_ok, self.user)
        approve_for_instance(self.instance, self.release_ok, self.user)

    def test_build_export_payload_filters_by_instance_approvals(self):
        payload = build_export_payload(self.instance)
        target_codes = {item["code"] for item in payload["targets"]}
        self.assertIn(self.target_ok.code, target_codes)
        self.assertNotIn(self.target_hidden.code, target_codes)

        indicator_codes = {item["code"] for item in payload["indicators"]}
        self.assertIn(self.indicator_ok.code, indicator_codes)

        evidence_titles = {item["title"] for item in payload["evidence"]}
        self.assertIn(self.evidence_ok.title, evidence_titles)

        dataset_titles = {item["title"] for item in payload["datasets"]}
        self.assertIn(self.dataset_ok.title, dataset_titles)

        release_versions = {item["version"] for item in payload["dataset_releases"]}
        self.assertIn(self.release_ok.version, release_versions)


class ExportWorkflowTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Org A")
        self.creator = User.objects.create_user(username="creator", password="pass1234", organisation=self.org)
        self.creator.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
        self.secretariat = User.objects.create_user(username="sec", password="pass1234", organisation=self.org)
        self.secretariat.groups.add(Group.objects.create(name=ROLE_SECRETARIAT))
        self.viewer = User.objects.create_user(username="viewer", password="pass1234", organisation=self.org)
        self.cycle = ReportingCycle.objects.create(
            code="CYCLE-2",
            title="Cycle 2",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            due_date=date(2026, 1, 31),
        )
        self.instance = ReportingInstance.objects.create(cycle=self.cycle, version_label="v1")

    def test_export_workflow_release_and_download_permissions(self):
        target = NationalTarget.objects.create(
            code="NT-OK",
            title="Target OK",
            organisation=self.org,
            created_by=self.creator,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        )
        approve_for_instance(self.instance, target, self.creator)
        package = ExportPackage.objects.create(
            title="Export A",
            organisation=self.org,
            created_by=self.creator,
            reporting_instance=self.instance,
        )

        submit_export_for_review(package, self.creator)
        approve_export(package, self.creator, note="ok")
        release_export(package, self.secretariat)

        package.refresh_from_db()
        self.assertEqual(package.status, ExportStatus.RELEASED)
        target_codes = {item["code"] for item in package.payload.get("targets", [])}
        self.assertIn(target.code, target_codes)

        self.client.force_login(self.secretariat)
        resp = self.client.get(reverse("nbms_app:export_package_download", args=[package.uuid]))
        self.assertEqual(resp.status_code, 200)

        self.client.force_login(self.viewer)
        resp = self.client.get(reverse("nbms_app:export_package_download", args=[package.uuid]))
        self.assertEqual(resp.status_code, 404)
