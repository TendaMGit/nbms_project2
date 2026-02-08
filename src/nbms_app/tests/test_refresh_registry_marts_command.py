from django.core.management import call_command

import pytest

from nbms_app.models import (
    AlienTaxonProfile,
    EcosystemRiskAssessment,
    EcosystemType,
    IucnRleCategory,
    LifecycleStatus,
    QaStatus,
    SensitivityLevel,
    TaxonConcept,
    TaxonGoldSummary,
    EcosystemGoldSummary,
    IASGoldSummary,
)


pytestmark = pytest.mark.django_db


def test_refresh_registry_marts_command_generates_summary_rows():
    ecosystem = EcosystemType.objects.create(
        ecosystem_code="ECO-MART-1",
        name="Mart ecosystem",
        biome="Fynbos",
        bioregion="Cape",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    EcosystemRiskAssessment.objects.create(
        ecosystem_type=ecosystem,
        assessment_year=2025,
        category=IucnRleCategory.EN,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    taxon = TaxonConcept.objects.create(
        taxon_code="TAX-MART-1",
        scientific_name="Species one",
        taxon_rank="species",
        is_native=True,
        has_national_voucher_specimen=True,
        voucher_specimen_count=2,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )
    AlienTaxonProfile.objects.create(
        taxon=taxon,
        country_code="ZA",
        is_invasive=True,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        qa_status=QaStatus.PUBLISHED,
    )

    call_command("refresh_registry_marts")

    assert TaxonGoldSummary.objects.exists()
    assert EcosystemGoldSummary.objects.exists()
    assert IASGoldSummary.objects.exists()
