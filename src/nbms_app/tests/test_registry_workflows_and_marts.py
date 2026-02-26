from datetime import date

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nbms_app.models import (
    AuditEvent,
    EcosystemGoldSummary,
    EcosystemType,
    EcosystemTypologyCrosswalk,
    Evidence,
    IucnGetNode,
    LifecycleStatus,
    QaStatus,
    RegistryEvidenceLink,
    SensitivityLevel,
    TaxonGoldSummary,
    User,
)


pytestmark = pytest.mark.django_db


def test_registry_transition_requires_evidence_for_approve_and_publishes_with_audit(client):
    admin = User.objects.create_superuser(
        username="registry-admin",
        email="registry-admin@example.org",
        password="pass1234",
    )
    ecosystem = EcosystemType.objects.create(
        ecosystem_code="ECO-TEST-01",
        name="Test ecosystem",
        status=LifecycleStatus.DRAFT,
        sensitivity=SensitivityLevel.INTERNAL,
        qa_status=QaStatus.DRAFT,
    )
    get_node = IucnGetNode.objects.create(level=3, code="3.1", label="Test node")
    crosswalk = EcosystemTypologyCrosswalk.objects.create(
        ecosystem_type=ecosystem,
        get_node=get_node,
        confidence=70,
        status=LifecycleStatus.DRAFT,
        sensitivity=SensitivityLevel.INTERNAL,
        qa_status=QaStatus.DRAFT,
    )
    evidence = Evidence.objects.create(
        title="Registry transition evidence",
        evidence_type="report",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )

    client.force_login(admin)
    submit_response = client.post(
        reverse("api_registry_transition", args=["ecosystem_crosswalk", crosswalk.uuid]),
        data={"action": "submit"},
        content_type="application/json",
    )
    assert submit_response.status_code == 200

    approve_without_evidence = client.post(
        reverse("api_registry_transition", args=["ecosystem_crosswalk", crosswalk.uuid]),
        data={"action": "approve"},
        content_type="application/json",
    )
    assert approve_without_evidence.status_code == 400

    link_response = client.post(
        reverse("api_registry_object_evidence", args=["ecosystem_crosswalk", crosswalk.uuid]),
        data={"evidence_uuid": str(evidence.uuid), "note": "Required for approval."},
        content_type="application/json",
    )
    assert link_response.status_code == 200

    approve_with_evidence = client.post(
        reverse("api_registry_transition", args=["ecosystem_crosswalk", crosswalk.uuid]),
        data={"action": "approve", "evidence_uuids": [str(evidence.uuid)]},
        content_type="application/json",
    )
    assert approve_with_evidence.status_code == 200
    publish_response = client.post(
        reverse("api_registry_transition", args=["ecosystem_crosswalk", crosswalk.uuid]),
        data={"action": "publish"},
        content_type="application/json",
    )
    assert publish_response.status_code == 200

    crosswalk.refresh_from_db()
    assert crosswalk.status == LifecycleStatus.PUBLISHED
    assert RegistryEvidenceLink.objects.filter(
        content_type=ContentType.objects.get_for_model(EcosystemTypologyCrosswalk),
        object_uuid=crosswalk.uuid,
        evidence=evidence,
    ).exists()
    assert AuditEvent.objects.filter(action="registry_submit", object_uuid=crosswalk.uuid).exists()
    assert AuditEvent.objects.filter(action="registry_approve", object_uuid=crosswalk.uuid).exists()
    assert AuditEvent.objects.filter(action="registry_publish", object_uuid=crosswalk.uuid).exists()


def test_registry_gold_summary_api_returns_rows(client):
    admin = User.objects.create_superuser(
        username="gold-admin",
        email="gold-admin@example.org",
        password="pass1234",
    )
    TaxonGoldSummary.objects.create(
        snapshot_date=date(2026, 1, 31),
        taxon_rank="species",
        is_native=True,
        is_endemic=False,
        has_voucher=True,
        is_ias=False,
        taxon_count=10,
        voucher_count=8,
        ias_profile_count=0,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    EcosystemGoldSummary.objects.create(
        snapshot_date=date(2026, 1, 31),
        dimension="province",
        dimension_key="WC",
        dimension_label="Western Cape",
        ecosystem_count=5,
        threatened_count=2,
        total_area_km2="1000.000",
        protected_area_km2="200.000",
        protected_percent="20.000",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    client.force_login(admin)

    taxa_response = client.get(reverse("api_registry_gold_summaries"), {"kind": "taxa"})
    assert taxa_response.status_code == 200
    taxa_payload = taxa_response.json()
    assert taxa_payload["kind"] == "taxa"
    assert taxa_payload["rows"]
    assert taxa_payload["rows"][0]["taxon_rank"] == "species"

    eco_response = client.get(reverse("api_registry_gold_summaries"), {"kind": "ecosystems"})
    assert eco_response.status_code == 200
    eco_payload = eco_response.json()
    assert eco_payload["kind"] == "ecosystems"
    assert eco_payload["rows"][0]["dimension"] == "province"
