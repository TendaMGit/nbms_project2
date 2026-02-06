from datetime import date

import pytest
from django.contrib.auth.models import Group

from nbms_app.models import (
    AuditEvent,
    Dataset,
    DatasetRelease,
    ExportPackage,
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
from nbms_app.services.exports import approve_export, release_export, submit_export_for_review
from nbms_app.services.instance_approvals import approve_for_instance
from nbms_app.services.workflows import approve, publish, submit_for_review


pytestmark = pytest.mark.django_db


def _base_reporting_instance():
    cycle = ReportingCycle.objects.create(
        code="CYCLE-AUDIT",
        title="Cycle Audit",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    return ReportingInstance.objects.create(cycle=cycle, version_label="v1")


def test_export_transitions_emit_audit_events():
    org = Organisation.objects.create(name="Org A", org_code="ORG-A")
    reviewer = User.objects.create_user(username="reviewer", password="pass1234", organisation=org)
    reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
    releaser = User.objects.create_user(username="releaser", password="pass1234", organisation=org)
    releaser.groups.add(Group.objects.create(name=ROLE_SECRETARIAT))

    instance = _base_reporting_instance()
    target = NationalTarget.objects.create(
        code="NT-AUD",
        title="Audit target",
        organisation=org,
        created_by=reviewer,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    approve_for_instance(instance, target, reviewer)
    package = ExportPackage.objects.create(
        title="Export Audit",
        organisation=org,
        created_by=reviewer,
        reporting_instance=instance,
    )

    submit_export_for_review(package, reviewer)
    approve_export(package, reviewer, note="ok")
    release_export(package, releaser)

    actions = set(
        AuditEvent.objects.filter(object_uuid=package.uuid).values_list("action", flat=True)
    )
    assert {"export_submit", "export_approve", "export_release"}.issubset(actions)


def test_indicator_publish_transition_audited():
    org = Organisation.objects.create(name="Org B", org_code="ORG-B")
    owner = User.objects.create_user(username="owner", password="pass1234", organisation=org)
    reviewer = User.objects.create_user(username="steward", password="pass1234", organisation=org)
    publisher = User.objects.create_user(username="sec", password="pass1234", organisation=org)
    reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
    publisher.groups.add(Group.objects.create(name=ROLE_SECRETARIAT))

    target = NationalTarget.objects.create(
        code="NT-IND",
        title="Target",
        organisation=org,
        created_by=owner,
    )
    indicator = Indicator.objects.create(
        code="IND-AUD",
        title="Indicator",
        national_target=target,
        organisation=org,
        created_by=owner,
    )

    submit_for_review(indicator, owner)
    approve(indicator, reviewer, note="qa complete")
    publish(indicator, publisher)

    actions = list(
        AuditEvent.objects.filter(object_uuid=indicator.uuid).values_list("action", flat=True)
    )
    assert "submit_for_review" in actions
    assert "approve" in actions
    assert "publish" in actions


def test_dataset_release_publish_transition_audited():
    org = Organisation.objects.create(name="Org C", org_code="ORG-C")
    owner = User.objects.create_user(username="dataset-owner", password="pass1234", organisation=org)
    reviewer = User.objects.create_user(username="dataset-steward", password="pass1234", organisation=org)
    publisher = User.objects.create_user(username="dataset-sec", password="pass1234", organisation=org)
    reviewer.groups.add(Group.objects.create(name=ROLE_DATA_STEWARD))
    publisher.groups.add(Group.objects.create(name=ROLE_SECRETARIAT))

    dataset = Dataset.objects.create(
        title="Dataset",
        organisation=org,
        created_by=owner,
    )
    release = DatasetRelease.objects.create(
        dataset=dataset,
        version="v1",
        snapshot_title="v1",
        snapshot_description="",
        snapshot_methodology="",
        organisation=org,
        created_by=owner,
    )

    submit_for_review(release, owner)
    approve(release, reviewer, note="ready")
    publish(release, publisher)

    actions = list(
        AuditEvent.objects.filter(object_uuid=release.uuid).values_list("action", flat=True)
    )
    assert "submit_for_review" in actions
    assert "approve" in actions
    assert "publish" in actions
