from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import (
    AlignmentRelationType,
    Dataset,
    DatasetRelease,
    Evidence,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    IndicatorReportingCapability,
    License,
    LifecycleStatus,
    Methodology,
    MethodologyIndicatorLink,
    MethodologyStatus,
    MethodologyVersion,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    QaStatus,
    RelationshipType,
    SensitivityLevel,
    UpdateFrequency,
)
from nbms_app.services.nba_pilot_ingest import (
    DEFAULT_MANIFEST_PATH,
    _build_disaggregation_schema,
    _ensure_framework_indicator,
    _ensure_framework_target,
    _indicator_type,
    _indicator_value_type,
)


DEMO_RELEASE_DATE = date(2024, 12, 31)

DEMO_INDICATORS = [
    {
        "code": "DEMO_ECO_EPLI_BIOME",
        "title": "Ecosystem Protection Level Index by Biome",
        "pack_id": "tepi_timeseries",
        "indicator_type": "headline",
        "unit": "index",
        "value_type": "index",
        "gbf_targets": ["3"],
        "coverage_geography": "National by biome",
        "points": [
            {"year": 2018, "value": "0.38", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
            {"year": 2020, "value": "0.41", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
            {"year": 2022, "value": "0.45", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
            {"year": 2024, "value": "0.49", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "target_progress": "ON_TRACK", "target_progress_label": "On track"}},
            {"year": 2018, "value": "0.31", "disaggregation": {"biome_code": "SAV", "biome_name": "Savanna", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
            {"year": 2020, "value": "0.34", "disaggregation": {"biome_code": "SAV", "biome_name": "Savanna", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
            {"year": 2022, "value": "0.37", "disaggregation": {"biome_code": "SAV", "biome_name": "Savanna", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
            {"year": 2024, "value": "0.40", "disaggregation": {"biome_code": "SAV", "biome_name": "Savanna", "target_progress": "ACCELERATE", "target_progress_label": "Needs acceleration"}},
        ],
    },
    {
        "code": "DEMO_ECO_EAI_TERR",
        "title": "Ecosystem Area Index",
        "pack_id": "ecosystem_extent",
        "indicator_type": "headline",
        "unit": "index",
        "value_type": "index",
        "gbf_targets": ["2"],
        "coverage_geography": "National by biome",
        "points": [
            {"year": 2018, "value": "0.92", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "ecosystem_type": "Fynbos composite", "ecosystem_type_label": "Fynbos composite"}},
            {"year": 2020, "value": "0.91", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "ecosystem_type": "Fynbos composite", "ecosystem_type_label": "Fynbos composite"}},
            {"year": 2022, "value": "0.90", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "ecosystem_type": "Fynbos composite", "ecosystem_type_label": "Fynbos composite"}},
            {"year": 2024, "value": "0.89", "disaggregation": {"biome_code": "FYN", "biome_name": "Fynbos", "ecosystem_type": "Fynbos composite", "ecosystem_type_label": "Fynbos composite"}},
            {"year": 2018, "value": "0.95", "disaggregation": {"biome_code": "SUK", "biome_name": "Succulent Karoo", "ecosystem_type": "Karoo composite", "ecosystem_type_label": "Karoo composite"}},
            {"year": 2020, "value": "0.95", "disaggregation": {"biome_code": "SUK", "biome_name": "Succulent Karoo", "ecosystem_type": "Karoo composite", "ecosystem_type_label": "Karoo composite"}},
            {"year": 2022, "value": "0.94", "disaggregation": {"biome_code": "SUK", "biome_name": "Succulent Karoo", "ecosystem_type": "Karoo composite", "ecosystem_type_label": "Karoo composite"}},
            {"year": 2024, "value": "0.94", "disaggregation": {"biome_code": "SUK", "biome_name": "Succulent Karoo", "ecosystem_type": "Karoo composite", "ecosystem_type_label": "Karoo composite"}},
        ],
    },
    {
        "code": "DEMO_SPECIES_BIRD_SPI",
        "title": "Bird Species Protection Level",
        "pack_id": "plant_spi_taxonomy",
        "indicator_type": "headline",
        "unit": "SPI",
        "value_type": "numeric",
        "gbf_targets": ["3"],
        "coverage_geography": "National by province and taxonomy",
        "points": [
            {"year": 2022, "value": "0.62", "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Aves", "taxonomy_order": "Accipitriformes", "taxonomy_family": "Accipitridae", "taxonomy_genus": "Aquila", "taxonomy_species": "Aquila verreauxii", "spi_category": "MP", "spi_category_label": "Moderately protected", "protection_category": "MP", "protection_category_label": "Moderately protected"}},
            {"year": 2024, "value": "0.71", "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Aves", "taxonomy_order": "Accipitriformes", "taxonomy_family": "Accipitridae", "taxonomy_genus": "Aquila", "taxonomy_species": "Aquila verreauxii", "spi_category": "WP", "spi_category_label": "Well protected", "protection_category": "WP", "protection_category_label": "Well protected"}},
            {"year": 2022, "value": "0.28", "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Aves", "taxonomy_order": "Gruiformes", "taxonomy_family": "Gruidae", "taxonomy_genus": "Balearica", "taxonomy_species": "Balearica regulorum", "spi_category": "PP", "spi_category_label": "Poorly protected", "protection_category": "PP", "protection_category_label": "Poorly protected"}},
            {"year": 2024, "value": "0.39", "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Aves", "taxonomy_order": "Gruiformes", "taxonomy_family": "Gruidae", "taxonomy_genus": "Balearica", "taxonomy_species": "Balearica regulorum", "spi_category": "PP", "spi_category_label": "Poorly protected", "protection_category": "PP", "protection_category_label": "Poorly protected"}},
        ],
    },
    {
        "code": "DEMO_SPECIES_FROG_THREAT",
        "title": "Amphibian Threat Status by Taxonomy",
        "pack_id": "species_threat_status",
        "indicator_type": "headline",
        "unit": "species",
        "value_type": "numeric",
        "gbf_targets": ["4"],
        "coverage_geography": "National by province and taxonomy",
        "points": [
            {"year": 2022, "value": "6", "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Amphibia", "taxonomy_order": "Anura", "taxonomy_family": "Pyxicephalidae", "taxonomy_genus": "Cacosternum", "taxonomy_species": "Cacosternum nanum", "threat_category": "EN", "threat_category_label": "Endangered"}},
            {"year": 2024, "value": "8", "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Amphibia", "taxonomy_order": "Anura", "taxonomy_family": "Pyxicephalidae", "taxonomy_genus": "Cacosternum", "taxonomy_species": "Cacosternum nanum", "threat_category": "CR", "threat_category_label": "Critically endangered"}},
            {"year": 2022, "value": "4", "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Amphibia", "taxonomy_order": "Anura", "taxonomy_family": "Heleophrynidae", "taxonomy_genus": "Heleophryne", "taxonomy_species": "Heleophryne rosei", "threat_category": "CR", "threat_category_label": "Critically endangered"}},
            {"year": 2024, "value": "5", "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Amphibia", "taxonomy_order": "Anura", "taxonomy_family": "Heleophrynidae", "taxonomy_genus": "Heleophryne", "taxonomy_species": "Heleophryne rosei", "threat_category": "CR", "threat_category_label": "Critically endangered"}},
        ],
    },
    {
        "code": "DEMO_BINARY_GBF_REPORTING_COMPLETENESS",
        "title": "GBF Reporting Completeness",
        "pack_id": "binary_admin_status",
        "indicator_type": "binary",
        "unit": "score",
        "value_type": "numeric",
        "gbf_targets": ["21"],
        "coverage_geography": "National administrative status",
        "points": [
            {"year": 2024, "value": "1", "disaggregation": {"policy_status": "approved", "policy_status_label": "Approved", "category": "complete", "category_label": "Complete"}},
        ],
    },
    {
        "code": "DEMO_BINARY_POLICY_ALIGNMENT",
        "title": "Policy Alignment for Biodiversity Mainstreaming",
        "pack_id": "binary_admin_status",
        "indicator_type": "binary",
        "unit": "score",
        "value_type": "numeric",
        "gbf_targets": ["14"],
        "coverage_geography": "National administrative status",
        "points": [
            {"year": 2024, "value": "1", "disaggregation": {"policy_status": "partially_aligned", "policy_status_label": "Partially aligned", "category": "in_progress", "category_label": "In progress"}},
        ],
    },
    {
        "code": "DEMO_BINARY_INVASIVE_RESPONSE_PLAN",
        "title": "Invasive Alien Species Response Plan",
        "pack_id": "binary_admin_status",
        "indicator_type": "binary",
        "unit": "score",
        "value_type": "numeric",
        "gbf_targets": ["6"],
        "coverage_geography": "National administrative status",
        "points": [
            {"year": 2024, "value": "1", "disaggregation": {"policy_status": "approved", "policy_status_label": "Approved", "category": "operational", "category_label": "Operational"}},
        ],
    },
    {
        "code": "DEMO_BINARY_BIOSAFETY_STATUS",
        "title": "Biosafety Governance Status",
        "pack_id": "binary_admin_status",
        "indicator_type": "binary",
        "unit": "score",
        "value_type": "numeric",
        "gbf_targets": ["17"],
        "coverage_geography": "National administrative status",
        "points": [
            {"year": 2024, "value": "0", "disaggregation": {"policy_status": "gap", "policy_status_label": "Gap", "category": "follow_up", "category_label": "Follow-up required"}},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed v2 indicator workflow demo catalogue, including NBA pilot ingest and additional UI demo indicators."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_indicator_workflow_v1")
        call_command("seed_demo_spatial")
        call_command("ingest_nba_pilot_outputs", manifest=str(DEFAULT_MANIFEST_PATH), log_file="media/ingest_reports/nba_pilot_v1.json")

        sanbi, _ = Organisation.objects.update_or_create(
            org_code="SANBI",
            defaults={"name": "SANBI", "is_active": True, "source_system": "nbms_seed", "source_ref": "indicator_workflow_v2"},
        )
        license_obj, _ = License.objects.update_or_create(
            code="CC-BY-4.0",
            defaults={
                "title": "Creative Commons Attribution 4.0 International",
                "url": "https://creativecommons.org/licenses/by/4.0/",
                "description": "Seeded public demo licence.",
                "is_active": True,
            },
        )

        seeded = 0
        for definition in DEMO_INDICATORS:
            indicator = _upsert_demo_indicator(definition=definition, organisation=sanbi, license_obj=license_obj)
            seeded += int(indicator.code == definition["code"])

        total = Indicator.objects.filter(status=LifecycleStatus.PUBLISHED).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded indicator workflow v2 extras={len(DEMO_INDICATORS)}, total published indicators={total}."
            )
        )


def _upsert_demo_indicator(*, definition: dict, organisation: Organisation, license_obj: License) -> Indicator:
    primary_target_code = definition["gbf_targets"][0]
    national_target, _ = NationalTarget.objects.update_or_create(
        code=f"DEMO-{definition['code']}",
        defaults={
            "title": definition["title"],
            "description": f"Demo target scaffold for {definition['title']}.",
            "responsible_org": organisation,
            "qa_status": QaStatus.PUBLISHED,
            "reporting_cadence": UpdateFrequency.ANNUAL,
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )
    indicator, _ = Indicator.objects.update_or_create(
        code=definition["code"],
        defaults={
            "title": definition["title"],
            "national_target": national_target,
            "indicator_type": _indicator_type(definition["indicator_type"]),
            "reporting_cadence": UpdateFrequency.ANNUAL,
            "qa_status": QaStatus.PUBLISHED,
            "responsible_org": organisation,
            "owner_organisation": organisation,
            "organisation": organisation,
            "license": license_obj,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "export_approved": True,
            "reporting_capability": IndicatorReportingCapability.YES,
            "update_frequency": UpdateFrequency.ANNUAL,
            "last_updated_on": DEMO_RELEASE_DATE,
            "coverage_geography": definition["coverage_geography"],
            "coverage_time_start_year": min(point["year"] for point in definition["points"]),
            "coverage_time_end_year": max(point["year"] for point in definition["points"]),
            "computation_notes": "Seeded v2 demo indicator for UI coverage and drilldowns.",
            "visual_pack_id": definition["pack_id"],
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )

    dataset, _ = Dataset.objects.update_or_create(
        dataset_code=f"DS-{definition['code']}",
        defaults={
            "title": definition["title"],
            "description": f"Seeded v2 dataset for {definition['title']}.",
            "methodology": "Seeded v2 demo dataset.",
            "source_url": "https://www.sanbi.org",
            "license": license_obj,
            "metadata_json": {"provider": "SANBI", "owner_org": "SANBI"},
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "export_approved": True,
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )
    IndicatorDatasetLink.objects.update_or_create(
        indicator=indicator,
        dataset=dataset,
        defaults={"note": "Seeded v2 dataset link."},
    )
    dataset_release, _ = DatasetRelease.objects.update_or_create(
        dataset=dataset,
        version="2024.1",
        defaults={
            "release_date": DEMO_RELEASE_DATE,
            "snapshot_title": f"{dataset.title} (2024.1)",
            "snapshot_description": dataset.description,
            "snapshot_methodology": dataset.methodology,
            "provenance_json": {"source": "seed_indicator_workflow_v2"},
            "asset_manifest_json": [],
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "export_approved": True,
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )

    methodology, _ = Methodology.objects.update_or_create(
        methodology_code=f"METH-{definition['code']}",
        defaults={
            "title": f"Methodology for {definition['title']}",
            "description": "Seeded v2 methodology.",
            "owner_org": organisation,
            "scope": "national",
            "references_url": "https://www.sanbi.org",
            "is_active": True,
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )
    method_version, _ = MethodologyVersion.objects.update_or_create(
        methodology=methodology,
        version="2.0",
        defaults={
            "status": MethodologyStatus.ACTIVE,
            "effective_date": DEMO_RELEASE_DATE,
            "change_log": "Seeded v2 demo methodology version.",
            "qa_steps_summary": "Seeded QA summary.",
            "approval_body": "NBMS Demo Seed",
            "is_active": True,
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )
    IndicatorMethodologyVersionLink.objects.update_or_create(
        indicator=indicator,
        methodology_version=method_version,
        defaults={"is_primary": True, "notes": "Seeded v2 methodology link.", "source": "seed_indicator_workflow_v2", "is_active": True},
    )
    MethodologyIndicatorLink.objects.update_or_create(
        methodology=methodology,
        indicator=indicator,
        defaults={
            "relationship_type": RelationshipType.DERIVED,
            "role": "primary",
            "notes": "Seeded v2 methodology relationship.",
            "is_active": True,
            "source_system": "nbms_seed",
            "source_ref": "indicator_workflow_v2",
        },
    )

    evidence, _ = Evidence.objects.update_or_create(
        evidence_code=f"EV-{definition['code']}",
        defaults={
            "title": f"Evidence for {definition['title']}",
            "description": "Seeded v2 evidence item.",
            "evidence_type": "report",
            "source_url": "https://www.sanbi.org",
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "export_approved": True,
        },
    )
    IndicatorEvidenceLink.objects.update_or_create(
        indicator=indicator,
        evidence=evidence,
        defaults={"note": "Seeded v2 evidence link."},
    )

    for target_code in definition["gbf_targets"]:
        framework_target = _ensure_framework_target(
            framework_code="GBF",
            target_code=target_code,
            target_title=f"GBF Target {target_code}",
            organisation=organisation,
        )
        framework_indicator = _ensure_framework_indicator(
            framework_target=framework_target,
            indicator_code=f"GBF-DEMO-{definition['code']}-{target_code}",
            indicator_title=definition["title"],
            organisation=organisation,
        )
        IndicatorFrameworkIndicatorLink.objects.update_or_create(
            indicator=indicator,
            framework_indicator=framework_indicator,
            defaults={
                "relation_type": AlignmentRelationType.SUPPORTS,
                "confidence": 70,
                "notes": "Seeded v2 GBF alignment.",
                "source": "seed_indicator_workflow_v2",
                "is_active": True,
            },
        )

    series, _ = IndicatorDataSeries.objects.update_or_create(
        indicator=indicator,
        defaults={
            "series_code": f"SER-{definition['code']}",
            "title": definition["title"],
            "unit": definition["unit"],
            "value_type": _indicator_value_type(definition["value_type"]),
            "methodology": "Seeded v2 demo series.",
            "disaggregation_schema": _build_disaggregation_schema(
                [{"disaggregation": point["disaggregation"]} for point in definition["points"]]
            ),
            "source_notes": "Seeded v2 demo series for UI validation.",
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "export_approved": True,
        },
    )
    IndicatorDataPoint.objects.filter(series=series, dataset_release=dataset_release).delete()
    IndicatorDataPoint.objects.bulk_create(
        [
            IndicatorDataPoint(
                series=series,
                year=point["year"],
                value_numeric=Decimal(str(point["value"])),
                disaggregation=point["disaggregation"],
                dataset_release=dataset_release,
                source_url="https://www.sanbi.org",
                footnote="Seeded v2 demonstration value.",
            )
            for point in definition["points"]
        ]
    )
    return indicator
