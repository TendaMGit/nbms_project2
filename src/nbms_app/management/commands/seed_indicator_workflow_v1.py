from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import (
    Dataset,
    DatasetCatalog,
    DatasetCatalogIndicatorLink,
    DatasetRelease,
    Evidence,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    IndicatorValueType,
    LifecycleStatus,
    Methodology,
    MethodologyIndicatorLink,
    MethodologyStatus,
    MethodologyVersion,
    MonitoringProgramme,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    ProgrammeIndicatorLink,
    ProgrammeDatasetLink,
    QaStatus,
    RelationshipType,
    SensitivityLevel,
    UpdateFrequency,
)


GBF_GOALS = [
    ("A", "The integrity, connectivity and resilience of all ecosystems are maintained, enhanced, or restored."),
    ("B", "Biodiversity is sustainably used and managed and nature's contributions to people are maintained."),
    ("C", "Monetary and non-monetary benefits from utilization of genetic resources are shared fairly."),
    ("D", "Adequate means of implementation are secured and equitably accessible to all Parties."),
]

GBF_TARGETS = [
    ("1", "Ensure all areas are under participatory integrated biodiversity-inclusive spatial planning.", "A"),
    ("2", "Restore at least 30 per cent of degraded ecosystems.", "A"),
    ("3", "Conserve and effectively manage at least 30 per cent of terrestrial and marine areas.", "A"),
    ("4", "Halt human-induced extinction and recover wild species.", "A"),
    ("5", "Ensure harvest, trade and use of wild species is legal and sustainable.", "B"),
    ("6", "Reduce impacts of invasive alien species by at least 50 per cent.", "B"),
    ("7", "Reduce pollution risks and the negative impact of pollution from all sources.", "B"),
    ("8", "Minimize impacts of climate change and ocean acidification on biodiversity.", "B"),
    ("9", "Ensure sustainable management and use of wild species.", "B"),
    ("10", "Enhance biodiversity and sustainability in agriculture, aquaculture, fisheries and forestry.", "B"),
    ("11", "Restore, maintain and enhance nature's contributions to people.", "B"),
    ("12", "Increase the area and quality of urban green and blue spaces.", "B"),
    ("13", "Implement measures to facilitate access and benefit sharing.", "C"),
    ("14", "Integrate biodiversity values into policies and planning.", "D"),
    ("15", "Ensure businesses monitor, assess and disclose biodiversity impacts.", "D"),
    ("16", "Enable sustainable consumption choices and reduce waste.", "D"),
    ("17", "Strengthen biosafety and biotechnology risk management.", "D"),
    ("18", "Identify and eliminate harmful incentives and subsidies.", "D"),
    ("19", "Increase financial resources from all sources.", "D"),
    ("20", "Strengthen capacity-building, technology transfer and cooperation.", "D"),
    ("21", "Ensure available data, information and knowledge for decision-making.", "D"),
    ("22", "Ensure participation, rights and equitable benefit sharing.", "D"),
    ("23", "Ensure gender equality and rights-based approach in biodiversity action.", "D"),
]

INDICATOR_PACK = [
    {
        "code": "NBMS-GBF-ECOSYSTEM-EXTENT",
        "title": "Ecosystem Extent by Ecosystem Type",
        "target_code": "1",
        "framework_indicator_code": "GBF-H1",
        "framework_indicator_title": "Headline Indicator: Retention of ecosystems",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "South Africa terrestrial and freshwater biomes",
        "data_points": [
            (2018, Decimal("100.0")),
            (2019, Decimal("99.4")),
            (2020, Decimal("98.8")),
            (2021, Decimal("98.1")),
            (2022, Decimal("97.7")),
        ],
    },
    {
        "code": "NBMS-GBF-ECOSYSTEM-THREAT",
        "title": "Ecosystem Threat Status Distribution",
        "target_code": "2",
        "framework_indicator_code": "GBF-H2",
        "framework_indicator_title": "Headline Indicator: Ecosystem restoration",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "National ecosystem classes",
        "data_points": [
            (2018, Decimal("34.0")),
            (2019, Decimal("33.7")),
            (2020, Decimal("33.3")),
            (2021, Decimal("32.9")),
            (2022, Decimal("32.4")),
        ],
    },
    {
        "code": "NBMS-GBF-PA-COVERAGE",
        "title": "Protected Area Coverage (Land)",
        "target_code": "3",
        "framework_indicator_code": "GBF-H3",
        "framework_indicator_title": "Headline Indicator: Protected area coverage",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "South Africa protected area estate",
        "data_points": [
            (2018, Decimal("14.9")),
            (2019, Decimal("15.2")),
            (2020, Decimal("15.7")),
            (2021, Decimal("16.3")),
            (2022, Decimal("17.1")),
        ],
    },
    {
        "code": "NBMS-GBF-IAS-PRESSURE",
        "title": "Invasive Alien Species Pressure Index",
        "target_code": "6",
        "framework_indicator_code": "GBF-H4",
        "framework_indicator_title": "Headline Indicator: Invasive alien species pressure",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "Priority catchments and ecosystems",
        "data_points": [
            (2018, Decimal("55.0")),
            (2019, Decimal("53.8")),
            (2020, Decimal("52.2")),
            (2021, Decimal("50.9")),
            (2022, Decimal("49.5")),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed GBF/NBA-inspired indicator workflow pack with datasets, methods, and monitoring programme links."

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

        gbf_framework, _ = Framework.objects.update_or_create(
            code="GBF",
            defaults={
                "title": "Kunming-Montreal Global Biodiversity Framework",
                "description": "Global biodiversity monitoring framework.",
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
                "organisation": sanbi,
            },
        )
        sdg_framework, _ = Framework.objects.update_or_create(
            code="SDG",
            defaults={
                "title": "Sustainable Development Goals (Biodiversity relevant subset)",
                "description": "SDG framework scaffold for biodiversity alignment.",
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
                "organisation": dffe,
            },
        )
        for code in ("RAMSAR", "CITES", "CMS"):
            Framework.objects.update_or_create(
                code=code,
                defaults={
                    "title": f"{code} Framework Scaffold",
                    "description": f"{code} scaffold for multi-MEA alignment.",
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "organisation": dffe,
                },
            )

        goal_map = {}
        for order, (goal_code, goal_title) in enumerate(GBF_GOALS, start=1):
            goal, _ = FrameworkGoal.objects.update_or_create(
                framework=gbf_framework,
                code=goal_code,
                defaults={
                    "title": f"Goal {goal_code}",
                    "description": goal_title,
                    "official_text": goal_title,
                    "sort_order": order,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "organisation": sanbi,
                    "is_active": True,
                },
            )
            goal_map[goal_code] = goal

        target_map = {}
        for target_code, target_title, goal_code in GBF_TARGETS:
            target, _ = FrameworkTarget.objects.update_or_create(
                framework=gbf_framework,
                code=target_code,
                defaults={
                    "goal": goal_map.get(goal_code),
                    "title": f"Target {target_code}",
                    "description": target_title,
                    "official_text": target_title,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "organisation": sanbi,
                },
            )
            target_map[target_code] = target

        for goal_code in ("14", "15"):
            FrameworkGoal.objects.update_or_create(
                framework=sdg_framework,
                code=goal_code,
                defaults={
                    "title": f"SDG {goal_code}",
                    "description": f"Sustainable Development Goal {goal_code}",
                    "sort_order": int(goal_code),
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "organisation": dffe,
                    "is_active": True,
                },
            )

        programme, _ = MonitoringProgramme.objects.update_or_create(
            programme_code="NBMS-MONITORING-CORE",
            defaults={
                "title": "NBMS Core Monitoring Programme",
                "description": "National programme for biodiversity indicators and GBF reporting.",
                "programme_type": "national",
                "lead_org": sanbi,
                "start_year": 2018,
                "geographic_scope": "South Africa",
                "spatial_coverage_description": "National extent",
                "taxonomic_scope": "Multi-taxa",
                "ecosystem_scope": "Terrestrial and freshwater",
                "objectives": "Produce nationally consistent indicator data for GBF and NBA reporting.",
                "sampling_design_summary": "Integrated sample-based and modelled estimation design.",
                "update_frequency": UpdateFrequency.ANNUAL,
                "qa_process_summary": "Peer review, stewardship checks, and release sign-off.",
                "website_url": "https://www.sanbi.org",
                "primary_contact_name": "NBMS Secretariat",
                "primary_contact_email": "nbms@example.org",
                "is_active": True,
                "source_system": "nbms_seed",
                "source_ref": "indicator_workflow_v1",
            },
        )

        created_indicators = 0
        for idx, item in enumerate(INDICATOR_PACK, start=1):
            national_target, _ = NationalTarget.objects.update_or_create(
                code=f"ZA-NT-{idx:02d}",
                defaults={
                    "title": f"National target supporting GBF target {item['target_code']}",
                    "description": "National implementation target for biodiversity outcomes.",
                    "responsible_org": dffe,
                    "qa_status": QaStatus.PUBLISHED,
                    "reporting_cadence": UpdateFrequency.ANNUAL,
                    "organisation": dffe,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )

            indicator, created = Indicator.objects.update_or_create(
                code=item["code"],
                defaults={
                    "title": item["title"],
                    "national_target": national_target,
                    "indicator_type": item["indicator_type"],
                    "reporting_cadence": UpdateFrequency.ANNUAL,
                    "qa_status": QaStatus.PUBLISHED,
                    "responsible_org": sanbi,
                    "owner_organisation": sanbi,
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "reporting_capability": "yes",
                    "update_frequency": "annual",
                    "coverage_geography": item["coverage_geography"],
                    "coverage_time_start_year": 2018,
                    "coverage_time_end_year": 2022,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )
            created_indicators += int(created)

            framework_indicator, _ = FrameworkIndicator.objects.update_or_create(
                framework=gbf_framework,
                code=item["framework_indicator_code"],
                defaults={
                    "framework_target": target_map[item["target_code"]],
                    "title": item["framework_indicator_title"],
                    "description": f"Framework indicator aligned to {item['title']}.",
                    "indicator_type": FrameworkIndicatorType.HEADLINE,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "organisation": sanbi,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )

            IndicatorFrameworkIndicatorLink.objects.update_or_create(
                indicator=indicator,
                framework_indicator=framework_indicator,
                defaults={
                    "relation_type": RelationshipType.SUPPORTING,
                    "confidence": 90,
                    "notes": "Seeded GBF alignment.",
                    "source": "seed_indicator_workflow_v1",
                    "is_active": True,
                },
            )

            methodology, _ = Methodology.objects.update_or_create(
                methodology_code=f"METH-{item['code']}",
                defaults={
                    "title": f"Methodology for {item['title']}",
                    "description": "Documented methodology for annual indicator computation.",
                    "owner_org": sanbi,
                    "scope": "national",
                    "references_url": "https://www.gbf-indicators.org/resources/indicator-factsheets/",
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )
            method_version, _ = MethodologyVersion.objects.update_or_create(
                methodology=methodology,
                version="1.0",
                defaults={
                    "status": MethodologyStatus.ACTIVE,
                    "effective_date": date(2022, 1, 1),
                    "change_log": "Initial approved seed version.",
                    "qa_steps_summary": "Reproducible script run and peer review.",
                    "peer_reviewed": True,
                    "approval_body": "NBMS Technical Committee",
                    "approval_reference": "NBMS-TC-2022-01",
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )
            IndicatorMethodologyVersionLink.objects.update_or_create(
                indicator=indicator,
                methodology_version=method_version,
                defaults={
                    "is_primary": True,
                    "notes": "Seeded as primary methodology link.",
                    "source": "seed_indicator_workflow_v1",
                    "is_active": True,
                },
            )
            MethodologyIndicatorLink.objects.update_or_create(
                methodology=methodology,
                indicator=indicator,
                defaults={
                    "relationship_type": RelationshipType.DERIVED,
                    "role": "primary",
                    "notes": "Seeded indicator-methodology relationship.",
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )

            dataset = Dataset.objects.update_or_create(
                title=f"Dataset for {item['title']}",
                defaults={
                    "description": "Core dataset supporting annual indicator computation.",
                    "methodology": "Compiled from monitoring programme observations and QA checks.",
                    "source_url": "https://www.sanbi.org",
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "export_approved": True,
                },
            )[0]
            IndicatorDatasetLink.objects.update_or_create(
                indicator=indicator,
                dataset=dataset,
                defaults={"note": "Primary input dataset."},
            )

            dataset_release, _ = DatasetRelease.objects.update_or_create(
                dataset=dataset,
                version="2022",
                defaults={
                    "release_date": date(2023, 6, 1),
                    "snapshot_title": f"{dataset.title} (2022 release)",
                    "snapshot_description": "Annual release used for reporting.",
                    "snapshot_methodology": dataset.methodology,
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "export_approved": True,
                },
            )

            dataset_catalog, _ = DatasetCatalog.objects.update_or_create(
                dataset_code=f"CAT-{item['code']}",
                defaults={
                    "title": dataset.title,
                    "description": dataset.description,
                    "dataset_type": "indicator_series",
                    "custodian_org": sanbi,
                    "producer_org": sanbi,
                    "access_level": "public",
                    "consent_required": False,
                    "update_frequency": UpdateFrequency.ANNUAL,
                    "file_formats": "csv,geojson",
                    "qa_status": QaStatus.PUBLISHED,
                    "keywords": "gbf,nbms,indicator",
                    "last_updated_date": date(2023, 6, 1),
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )
            DatasetCatalogIndicatorLink.objects.update_or_create(
                dataset=dataset_catalog,
                indicator=indicator,
                defaults={
                    "relationship_type": RelationshipType.DERIVED,
                    "role": "source",
                    "notes": "Seeded catalog-indicator linkage.",
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )
            ProgrammeDatasetLink.objects.update_or_create(
                programme=programme,
                dataset=dataset_catalog,
                defaults={
                    "relationship_type": RelationshipType.LEAD,
                    "role": "core_dataset",
                    "notes": "Dataset sourced through NBMS core programme.",
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )

            ProgrammeIndicatorLink.objects.update_or_create(
                programme=programme,
                indicator=indicator,
                defaults={
                    "relationship_type": RelationshipType.LEAD,
                    "role": "core_indicator",
                    "notes": "Indicator sourced from NBMS core programme.",
                    "is_active": True,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                },
            )

            series, _ = IndicatorDataSeries.objects.update_or_create(
                indicator=indicator,
                defaults={
                    "title": item["title"],
                    "unit": "index",
                    "value_type": IndicatorValueType.NUMERIC,
                    "methodology": "Annual aggregated indicator value.",
                    "disaggregation_schema": {
                        "province": {"type": "string"},
                        "realm": {"type": "string"},
                    },
                    "source_notes": "Seeded for workflow validation and dashboard tests.",
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "export_approved": True,
                },
            )

            for year, value in item["data_points"]:
                IndicatorDataPoint.objects.update_or_create(
                    series=series,
                    year=year,
                    disaggregation={"province": "ALL", "realm": "national"},
                    dataset_release=dataset_release,
                    defaults={
                        "value_numeric": value,
                        "value_text": "",
                        "source_url": "https://www.sanbi.org",
                        "footnote": "Seeded demonstration value.",
                    },
                )

            evidence, _ = Evidence.objects.update_or_create(
                title=f"Evidence for {item['title']}",
                defaults={
                    "description": "Supporting evidence package for seeded indicator.",
                    "evidence_type": "report",
                    "source_url": "https://www.sanbi.org",
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "export_approved": True,
                },
            )
            IndicatorEvidenceLink.objects.update_or_create(
                indicator=indicator,
                evidence=evidence,
                defaults={"note": "Required evidence for publish workflow."},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded indicator workflow pack. Indicators created={created_indicators}, "
                f"total indicators={Indicator.objects.count()}, total GBF targets={len(GBF_TARGETS)}."
            )
        )
