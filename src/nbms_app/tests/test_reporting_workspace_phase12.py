from __future__ import annotations

from datetime import date
import json
import hashlib
import io
from zipfile import ZipFile

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.files.storage import default_storage
from django.urls import reverse

from nbms_app.models import (
    Evidence,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SectionIIINationalTargetProgress,
    User,
)
from nbms_app.services.authorization import (
    ROLE_PUBLISHING_AUTHORITY,
    ROLE_SECTION_LEAD,
    ROLE_SECRETARIAT,
    ROLE_SYSTEM_ADMIN,
    ROLE_TECHNICAL_COMMITTEE,
)


pytestmark = pytest.mark.django_db


def _mk_user(org, username, role_names):
    user = User.objects.create_user(
        username=username,
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    for role in role_names:
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


def _mk_instance(org):
    cycle = ReportingCycle.objects.create(
        code="NR7",
        title="Seventh National Report",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        due_date=date(2027, 3, 1),
        default_language="English",
        allowed_languages=["English"],
        is_active=True,
    )
    return ReportingInstance.objects.create(
        cycle=cycle,
        version_label="v1",
        report_title="South Africa NR7",
        country_name="South Africa",
        focal_point_org=org,
        publishing_authority_org=org,
        is_public=False,
    )


def _seed_section_content(client, instance):
    section_payload = {
        "country_name": "South Africa",
        "authorities": ["SANBI", "DFFE"],
        "contact_name": "Demo Contact",
        "contact_email": "demo@example.org",
        "preparation_process": "Structured drafting process.",
        "coordination_mechanisms": "Cross-sector coordination.",
        "consultations": "Consultations completed.",
        "challenges_encountered": "Data gaps in some indicators.",
    }
    response = client.post(
        reverse("api_reporting_workspace_section", args=[instance.uuid, "section-i"]),
        {"response_json": section_payload, "base_version": 1},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_workspace_collaboration_workflow_exports_and_dossier(client):
    call_command("bootstrap_roles")
    call_command("seed_mea_template_packs")

    org = Organisation.objects.create(name="SANBI", org_code="SANBI")
    author = _mk_user(org, "author", [ROLE_SECTION_LEAD])
    technical = _mk_user(org, "technical", [ROLE_TECHNICAL_COMMITTEE])
    secretariat = _mk_user(org, "secretariat", [ROLE_SECRETARIAT])
    publishing = _mk_user(org, "publishing", [ROLE_PUBLISHING_AUTHORITY])
    admin = _mk_user(org, "sysadmin", [ROLE_SYSTEM_ADMIN])
    admin.is_superuser = True
    admin.save(update_fields=["is_superuser"])
    instance = _mk_instance(org)

    client.force_login(author)
    workspace_response = client.get(reverse("api_reporting_workspace_summary", args=[instance.uuid]))
    assert workspace_response.status_code == 200
    payload = workspace_response.json()
    assert payload["pack"]["code"] == "cbd_national_report_v1"
    assert payload["instance"]["cycle_code"] == "NR7"

    _seed_section_content(client, instance)

    suggestion_response = client.post(
        reverse("api_reporting_workspace_section", args=[instance.uuid, "section-i"]),
        {
            "base_version": 2,
            "suggestion_mode": True,
            "patch_json": {"contact_phone": "+27-10-000-0000"},
            "response_json": {},
            "rationale": "Add missing phone contact.",
        },
        content_type="application/json",
    )
    assert suggestion_response.status_code == 201
    suggestion_uuid = suggestion_response.json()["suggested_change_uuid"]

    comments_response = client.post(
        reverse("api_reporting_workspace_section_comments", args=[instance.uuid, "section-i"]),
        {"json_path": "contact_phone", "body": "Please verify this number."},
        content_type="application/json",
    )
    assert comments_response.status_code == 200

    # Submit and section approvals
    submit_response = client.post(
        reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
        {"action": "submit"},
        content_type="application/json",
    )
    assert submit_response.status_code == 200

    sections = payload["sections"]
    for row in sections:
        approve_response = client.post(
            reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
            {"action": "section_approve", "section_code": row["section_code"]},
            content_type="application/json",
        )
        assert approve_response.status_code == 200

    # Technical approval initially blocked by evidence gate
    client.force_login(technical)
    tech_blocked = client.post(
        reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
        {"action": "technical_approve"},
        content_type="application/json",
    )
    assert tech_blocked.status_code == 400

    target = NationalTarget.objects.create(
        code="NT-001",
        title="Target 1",
        organisation=org,
    )
    evidence = Evidence.objects.create(
        evidence_code="EV-001",
        title="Section III evidence",
        evidence_type="report",
        organisation=org,
    )
    progress = SectionIIINationalTargetProgress.objects.create(
        reporting_instance=instance,
        national_target=target,
    )
    progress.evidence_items.add(evidence)

    tech_ok = client.post(
        reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
        {"action": "technical_approve"},
        content_type="application/json",
    )
    assert tech_ok.status_code == 200

    client.force_login(secretariat)
    consolidate = client.post(
        reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
        {"action": "consolidate"},
        content_type="application/json",
    )
    assert consolidate.status_code == 200

    client.force_login(publishing)
    publish_ok = client.post(
        reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
        {"action": "publishing_approve"},
        content_type="application/json",
    )
    assert publish_ok.status_code == 200
    instance.refresh_from_db()
    assert instance.status == "submitted"
    assert instance.finalized_at is not None

    # Suggestions can be accepted after unlocking by system admin.
    client.force_login(admin)
    unlock = client.post(
        reverse("api_reporting_workspace_workflow_action", args=[instance.uuid]),
        {"action": "unlock"},
        content_type="application/json",
    )
    assert unlock.status_code == 200
    decide = client.post(
        reverse(
            "api_reporting_workspace_suggestion_decide",
            args=[instance.uuid, "section-i", suggestion_uuid],
        ),
        {"action": "accept"},
        content_type="application/json",
    )
    assert decide.status_code == 200

    # Export surfaces
    export_pdf = client.get(reverse("api_reporting_workspace_export_pdf", args=[instance.uuid]))
    assert export_pdf.status_code == 200
    assert export_pdf["Content-Type"] == "application/pdf"
    export_docx = client.get(reverse("api_reporting_workspace_export_docx", args=[instance.uuid]))
    assert export_docx.status_code == 200
    assert export_docx["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    export_json = client.get(reverse("api_reporting_workspace_export_json", args=[instance.uuid]))
    assert export_json.status_code == 200
    assert export_json["Content-Type"] == "application/json"

    dossier_create = client.post(reverse("api_reporting_workspace_generate_dossier", args=[instance.uuid]))
    assert dossier_create.status_code == 201
    dossier_latest = client.get(reverse("api_reporting_workspace_latest_dossier", args=[instance.uuid]))
    assert dossier_latest.status_code == 200
    dossier_payload = dossier_latest.json()["dossier"]
    assert "content_hash" in dossier_payload
    with default_storage.open(dossier_payload["storage_path"], mode="rb") as fh:
        payload = fh.read()
    assert hashlib.sha256(payload).hexdigest() == dossier_payload["content_hash"]
    with ZipFile(io.BytesIO(payload), "r") as zf:
        names = sorted(zf.namelist())
        assert names == [
            "audit_log.json",
            "evidence_manifest.json",
            "integrity.json",
            "report.docx",
            "report.pdf",
            "submission.json",
            "visibility.json",
        ]
        integrity = json.loads(zf.read("integrity.json").decode("utf-8"))
        pdf_hash = hashlib.sha256(zf.read("report.pdf")).hexdigest()
        docx_hash = hashlib.sha256(zf.read("report.docx")).hexdigest()
        json_hash = hashlib.sha256(zf.read("submission.json")).hexdigest()
        assert integrity["export_hashes"]["pdf_hash"] == pdf_hash
        assert integrity["export_hashes"]["docx_hash"] == docx_hash
        assert integrity["export_hashes"]["json_hash"] == json_hash


def test_internal_report_blocks_unauthorized_dossier_access(client):
    call_command("seed_mea_template_packs")
    org = Organisation.objects.create(name="SANBI", org_code="SANBI")
    authorised = User.objects.create_user("authorised", password="pass1234", organisation=org, is_staff=True)
    outsider = User.objects.create_user("outsider", password="pass1234", is_staff=True)
    instance = _mk_instance(org)

    client.force_login(authorised)
    created = client.post(reverse("api_reporting_workspace_generate_dossier", args=[instance.uuid]))
    assert created.status_code == 201

    client.force_login(outsider)
    blocked = client.get(reverse("api_reporting_workspace_latest_dossier", args=[instance.uuid]))
    assert blocked.status_code == 403
