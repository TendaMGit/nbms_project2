from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import (
    DataAgreement,
    DatasetCatalog,
    Indicator,
    MonitoringProgramme,
    MonitoringProgrammeSteward,
    Organisation,
    ProgrammeRefreshCadence,
    ProgrammeStewardRole,
    RelationshipType,
    SensitivityClass,
    UpdateFrequency,
    User,
)
from nbms_app.services.programme_ops import queue_programme_run


class Command(BaseCommand):
    help = "Seed monitoring programme operations scaffolding with run history and governance metadata."

    @transaction.atomic
    def handle(self, *args, **options):
        sanbi, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute", "org_type": "Government"},
        )
        dffe, _ = Organisation.objects.get_or_create(
            org_code="DFFE",
            defaults={"name": "Department of Forestry, Fisheries and the Environment", "org_type": "Government"},
        )
        saeon, _ = Organisation.objects.get_or_create(
            org_code="SAEON",
            defaults={"name": "South African Environmental Observation Network", "org_type": "Research"},
        )

        sensitivity, _ = SensitivityClass.objects.get_or_create(
            sensitivity_code="INT",
            defaults={
                "sensitivity_name": "Internal programme operations",
                "access_level_default": "internal",
                "consent_required_default": False,
                "is_active": True,
            },
        )
        agreement, _ = DataAgreement.objects.get_or_create(
            agreement_code="NBMS-BIRDIE-MOU",
            defaults={
                "title": "NBMS-BIRDIE Data Integration MOU",
                "agreement_type": "MOU",
                "status": "active",
                "is_active": True,
            },
        )
        agreement.parties.add(sanbi, dffe, saeon)

        steward, created = User.objects.get_or_create(
            username="programme_steward",
            defaults={
                "email": "programme.steward@nbms.local",
                "first_name": "Programme",
                "last_name": "Steward",
                "organisation": sanbi,
                "is_staff": True,
            },
        )
        if created:
            steward.set_unusable_password()
            steward.save(update_fields=["password"])

        core_programme, _ = MonitoringProgramme.objects.update_or_create(
            programme_code="NBMS-CORE-PROGRAMME",
            defaults={
                "title": "NBMS Core Indicator Operations",
                "description": "Core national indicator ingestion, QA, compute, and release programme.",
                "programme_type": "national",
                "lead_org": sanbi,
                "refresh_cadence": ProgrammeRefreshCadence.MONTHLY,
                "update_frequency": UpdateFrequency.MONTHLY,
                "scheduler_enabled": True,
                "geographic_scope": "South Africa",
                "taxonomic_scope": "National biodiversity indicators",
                "ecosystem_scope": "Terrestrial, freshwater and marine realms",
                "objectives": "Provide deterministic indicator workflows for GBF and national reporting.",
                "sampling_design_summary": "Integrated national datasets with annual and quarterly refreshes.",
                "qa_process_summary": "Automated validation rules plus steward review before publish.",
                "sensitivity_class": sensitivity,
                "consent_required": False,
                "is_active": True,
                "pipeline_definition_json": {
                    "steps": [
                        {"key": "ingest_core", "type": "ingest"},
                        {"key": "validate_core", "type": "validate"},
                        {"key": "compute_core", "type": "compute"},
                        {"key": "publish_core", "type": "publish"},
                    ]
                },
                "data_quality_rules_json": {
                    "minimum_dataset_links": 1,
                    "minimum_indicator_links": 1,
                },
                "lineage_notes": "Bronze->silver->gold lineage tracked in run summaries.",
            },
        )
        core_programme.partners.set([dffe])
        core_programme.operating_institutions.set([sanbi, dffe])
        MonitoringProgrammeSteward.objects.update_or_create(
            programme=core_programme,
            user=steward,
            role=ProgrammeStewardRole.OWNER,
            defaults={"is_primary": True, "is_active": True},
        )

        birdie_programme, _ = MonitoringProgramme.objects.update_or_create(
            programme_code="NBMS-BIRDIE-INTEGRATION",
            defaults={
                "title": "NBMS BIRDIE Integration Programme",
                "description": "External pipeline ingest and harmonisation workflow for waterbird indicators.",
                "programme_type": "national",
                "lead_org": sanbi,
                "refresh_cadence": ProgrammeRefreshCadence.WEEKLY,
                "update_frequency": UpdateFrequency.WEEKLY if hasattr(UpdateFrequency, "WEEKLY") else UpdateFrequency.MONTHLY,
                "scheduler_enabled": True,
                "geographic_scope": "South Africa wetlands and flyway-relevant sites",
                "taxonomic_scope": "Waterbirds and wetland indicator species",
                "ecosystem_scope": "Wetlands and connected catchments",
                "objectives": "Integrate BIRDIE API outputs into NBMS-ready indicator marts.",
                "sampling_design_summary": "API pulls by site/species/province with model version provenance.",
                "qa_process_summary": "Connector validation + steward review before publish.",
                "sensitivity_class": sensitivity,
                "consent_required": False,
                "agreement": agreement,
                "is_active": True,
                "pipeline_definition_json": {
                    "steps": [
                        {"key": "ingest_birdie_api", "type": "ingest"},
                        {"key": "validate_birdie_payloads", "type": "validate"},
                        {"key": "compute_waterbird_metrics", "type": "compute"},
                        {"key": "publish_readiness", "type": "publish"},
                    ]
                },
                "data_quality_rules_json": {
                    "minimum_dataset_links": 1,
                    "minimum_indicator_links": 1,
                },
                "lineage_notes": "Raw connector payloads retained for replay and method parity checks.",
            },
        )
        birdie_programme.partners.set([dffe, saeon])
        birdie_programme.operating_institutions.set([sanbi, dffe, saeon])
        MonitoringProgrammeSteward.objects.update_or_create(
            programme=birdie_programme,
            user=steward,
            role=ProgrammeStewardRole.OPERATOR,
            defaults={"is_primary": True, "is_active": True},
        )

        datasets = list(DatasetCatalog.objects.filter(is_active=True).order_by("dataset_code", "id")[:2])
        indicators = list(Indicator.objects.order_by("code", "id")[:4])
        if datasets:
            for dataset in datasets:
                core_programme.dataset_links.update_or_create(
                    dataset=dataset,
                    defaults={
                        "relationship_type": RelationshipType.SUPPORTING,
                        "role": "primary_input",
                        "is_active": True,
                    },
                )
            birdie_programme.dataset_links.update_or_create(
                dataset=datasets[0],
                defaults={
                    "relationship_type": RelationshipType.DERIVED,
                    "role": "external_connector",
                    "is_active": True,
                },
            )
        if indicators:
            for indicator in indicators[:2]:
                core_programme.indicator_links.update_or_create(
                    indicator=indicator,
                    defaults={
                        "relationship_type": RelationshipType.LEAD,
                        "role": "core_indicator",
                        "is_active": True,
                    },
                )
            for indicator in indicators[2:4]:
                birdie_programme.indicator_links.update_or_create(
                    indicator=indicator,
                    defaults={
                        "relationship_type": RelationshipType.SUPPORTING,
                        "role": "birdie_fed_indicator",
                        "is_active": True,
                    },
                )

        if not core_programme.runs.exists():
            queue_programme_run(
                programme=core_programme,
                requested_by=steward,
                run_type="full",
                dry_run=False,
                execute_now=True,
            )
        if not birdie_programme.runs.exists():
            queue_programme_run(
                programme=birdie_programme,
                requested_by=steward,
                run_type="ingest",
                dry_run=True,
                execute_now=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded programme ops v1: NBMS-CORE-PROGRAMME and NBMS-BIRDIE-INTEGRATION with run history."
            )
        )
