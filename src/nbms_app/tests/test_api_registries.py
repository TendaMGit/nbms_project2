import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    AlienTaxonProfile,
    EICATAssessment,
    EicatCategory,
    EcosystemType,
    IASCountryChecklistRecord,
    LifecycleStatus,
    MonitoringProgramme,
    Organisation,
    ProgrammeTemplate,
    ProgrammeTemplateDomain,
    QaStatus,
    RegistryReviewStatus,
    SensitivityLevel,
    SpecimenVoucher,
    TaxonConcept,
    User,
)
from nbms_app.services.authorization import ROLE_SECURITY_OFFICER


pytestmark = pytest.mark.django_db


def _auth_client(client, user):
    assert client.login(username=user.username, password="pass1234")
    return client


def test_registry_ecosystems_abac_no_leak(client):
    org_a = Organisation.objects.create(name="Org A", org_code="ORG-A")
    org_b = Organisation.objects.create(name="Org B", org_code="ORG-B")
    user = User.objects.create_user(username="eco-user", password="pass1234", organisation=org_a, is_staff=True)

    visible = EcosystemType.objects.create(
        ecosystem_code="ECO-001",
        name="Visible ecosystem",
        realm="terrestrial",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
        export_approved=True,
    )
    hidden = EcosystemType.objects.create(
        ecosystem_code="ECO-999",
        name="Hidden ecosystem",
        realm="marine",
        organisation=org_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.RESTRICTED,
        qa_status=QaStatus.PUBLISHED,
        export_approved=False,
    )

    _auth_client(client, user)
    response = client.get(reverse("api_registry_ecosystems"))
    assert response.status_code == 200
    codes = [row["ecosystem_code"] for row in response.json()["results"]]
    assert visible.ecosystem_code in codes
    assert hidden.ecosystem_code not in codes

    detail_response = client.get(reverse("api_registry_ecosystem_detail", args=[hidden.uuid]))
    assert detail_response.status_code == 404


def test_registry_taxon_detail_masks_sensitive_voucher_coordinates(client):
    org = Organisation.objects.create(name="Org Taxon", org_code="ORG-TAX")
    viewer = User.objects.create_user(username="taxon-viewer", password="pass1234", organisation=org, is_staff=True)
    security = User.objects.create_user(username="taxon-sec", password="pass1234", organisation=org, is_staff=True)
    security_group, _ = Group.objects.get_or_create(name=ROLE_SECURITY_OFFICER)
    security.groups.add(security_group)

    taxon = TaxonConcept.objects.create(
        taxon_code="TAX-001",
        scientific_name="Acacia mearnsii",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
        export_approved=True,
    )
    SpecimenVoucher.objects.create(
        taxon=taxon,
        occurrence_id="OCC-1",
        locality="Sensitive locality",
        decimal_latitude="-26.1234567",
        decimal_longitude="27.7654321",
        has_sensitive_locality=True,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.RESTRICTED,
        qa_status=QaStatus.PUBLISHED,
    )

    _auth_client(client, viewer)
    response = client.get(reverse("api_registry_taxon_detail", args=[taxon.uuid]))
    assert response.status_code == 200
    voucher = response.json()["vouchers"][0]
    assert voucher["locality"] == "Restricted locality"
    assert voucher["decimal_latitude"] is None
    assert voucher["decimal_longitude"] is None
    client.logout()

    _auth_client(client, security)
    response = client.get(reverse("api_registry_taxon_detail", args=[taxon.uuid]))
    assert response.status_code == 200
    voucher = response.json()["vouchers"][0]
    assert voucher["locality"] == "Sensitive locality"
    assert voucher["decimal_latitude"] is not None
    assert voucher["decimal_longitude"] is not None


def test_registry_ias_filters_and_detail(client):
    org = Organisation.objects.create(name="Org IAS", org_code="ORG-IAS")
    user = User.objects.create_user(username="ias-user", password="pass1234", organisation=org, is_staff=True)
    taxon = TaxonConcept.objects.create(
        taxon_code="IAS-TAX-1",
        scientific_name="Opuntia ficus-indica",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    profile = AlienTaxonProfile.objects.create(
        taxon=taxon,
        country_code="ZA",
        establishment_means_code="introduced",
        degree_of_establishment_code="invasive",
        pathway_code="release",
        is_invasive=True,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    IASCountryChecklistRecord.objects.create(
        taxon=taxon,
        scientific_name=taxon.scientific_name,
        country_code="ZA",
        source_dataset="GRIIS South Africa",
        source_system="griis_za",
        source_identifier="GRIIS-ZA-001",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    EICATAssessment.objects.create(
        profile=profile,
        category=EicatCategory.MR,
        review_status=RegistryReviewStatus.IN_REVIEW,
        status=LifecycleStatus.DRAFT,
        sensitivity=SensitivityLevel.INTERNAL,
        qa_status=QaStatus.DRAFT,
        source_system="manual",
        source_ref="IAS-TAX-1",
    )

    _auth_client(client, user)
    list_response = client.get(reverse("api_registry_ias"), {"eicat": "MR"})
    assert list_response.status_code == 200
    results = list_response.json()["results"]
    assert len(results) == 1
    assert results[0]["taxon_code"] == "IAS-TAX-1"

    detail_response = client.get(reverse("api_registry_ias_detail", args=[profile.uuid]))
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["profile"]["taxon_code"] == "IAS-TAX-1"
    assert payload["checklist_records"][0]["source_identifier"] == "GRIIS-ZA-001"


def test_programme_templates_endpoint_exposes_linked_programmes(client):
    org = Organisation.objects.create(name="Org Templates", org_code="ORG-TEMP")
    user = User.objects.create_user(username="template-user", password="pass1234", organisation=org, is_staff=True)
    ProgrammeTemplate.objects.create(
        template_code="NBMS-PROG-ECOSYSTEMS",
        title="Ecosystems",
        domain=ProgrammeTemplateDomain.ECOSYSTEMS,
        pipeline_definition_json={"steps": []},
        required_outputs_json=[],
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    programme = MonitoringProgramme.objects.create(
        programme_code="NBMS-PROG-ECOSYSTEMS",
        title="Ecosystem Programme",
        programme_type="national",
        lead_org=org,
        is_active=True,
    )

    _auth_client(client, user)
    response = client.get(reverse("api_programme_templates"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["templates"][0]["template_code"] == "NBMS-PROG-ECOSYSTEMS"
    assert payload["templates"][0]["linked_programme_uuid"] == str(programme.uuid)
