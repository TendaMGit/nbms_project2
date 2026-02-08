import pytest
from django.core.management import call_command

from nbms_app.models import (
    AlienTaxonProfile,
    EcosystemRiskAssessment,
    IucnGetNode,
    IASCountryChecklistRecord,
    MonitoringProgramme,
    ProgrammeTemplate,
    SpecimenVoucher,
    TaxonConcept,
    TaxonSourceRecord,
)


pytestmark = pytest.mark.django_db


def test_seed_get_reference_idempotent():
    call_command("seed_get_reference")
    call_command("seed_get_reference")
    assert IucnGetNode.objects.filter(is_active=True).count() >= 10


def test_sync_taxon_backbone_seed_demo_and_vouchers():
    call_command("sync_taxon_backbone", "--seed-demo", "--skip-remote")
    call_command("sync_specimen_vouchers", "--seed-demo")
    assert TaxonConcept.objects.count() >= 4
    assert TaxonSourceRecord.objects.count() >= 4
    assert SpecimenVoucher.objects.count() >= 2


def test_sync_griis_seed_demo_creates_ias_profiles_and_assessments():
    call_command("sync_griis_za", "--seed-demo")
    assert IASCountryChecklistRecord.objects.count() >= 2
    assert AlienTaxonProfile.objects.count() >= 2


def test_seed_programme_templates_instantiates_programmes():
    call_command("seed_programme_templates", "--instantiate")
    assert ProgrammeTemplate.objects.filter(template_code="NBMS-PROG-ECOSYSTEMS").exists()
    assert MonitoringProgramme.objects.filter(programme_code="NBMS-PROG-ECOSYSTEMS").exists()
    assert MonitoringProgramme.objects.filter(programme_code="NBMS-PROG-IAS").exists()


def test_seed_registry_demo_populates_rle_ready_rows():
    call_command("seed_registry_demo")
    assert TaxonConcept.objects.exists()
    assert IASCountryChecklistRecord.objects.exists()
    assert IucnGetNode.objects.exists()
    assert EcosystemRiskAssessment.objects.count() >= 0


def test_seed_shortcut_commands_execute():
    call_command("seed_taxon_demo")
    call_command("seed_ias_demo")
    assert TaxonConcept.objects.exists()
    assert IASCountryChecklistRecord.objects.exists()
