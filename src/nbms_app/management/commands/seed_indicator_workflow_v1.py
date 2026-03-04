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
    IndicatorInputRequirement,
    IndicatorMethodProfile,
    IndicatorMethodReadiness,
    IndicatorMethodType,
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
    SpatialLayer,
    SpatialSource,
    SpatialUnit,
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
        "data_points": [(2018, Decimal("34.0")), (2019, Decimal("33.7")), (2020, Decimal("33.3")), (2021, Decimal("32.9")), (2022, Decimal("32.4"))],
    },
    {
        "code": "NBMS-GBF-ECOSYSTEM-PROTECTION",
        "title": "Ecosystem Protection Level",
        "target_code": "3",
        "framework_indicator_code": "GBF-H3A",
        "framework_indicator_title": "Headline Indicator: Ecosystem protection level",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "South African terrestrial ecosystems",
        "data_points": [(2018, Decimal("42.0")), (2019, Decimal("42.6")), (2020, Decimal("43.1")), (2021, Decimal("44.0")), (2022, Decimal("44.8"))],
    },
    {
        "code": "NBMS-GBF-SPECIES-THREAT",
        "title": "Species Threat Status by Taxonomic Group",
        "target_code": "4",
        "framework_indicator_code": "GBF-H4A",
        "framework_indicator_title": "Headline Indicator: Species threat status",
        "indicator_type": NationalIndicatorType.HEADLINE,
        "coverage_geography": "Priority threatened taxa across South Africa",
        "data_points": [(2018, Decimal("108.0")), (2019, Decimal("112.0")), (2020, Decimal("118.0")), (2021, Decimal("122.0")), (2022, Decimal("127.0"))],
    },
    {
        "code": "NBMS-GBF-SPECIES-PROTECTION",
        "title": "Species Protection Level by Taxonomic Group",
        "target_code": "4",
        "framework_indicator_code": "GBF-H4B",
        "framework_indicator_title": "Headline Indicator: Species protection level",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "Priority taxonomic groups with conservation action",
        "data_points": [(2018, Decimal("47.0")), (2019, Decimal("48.4")), (2020, Decimal("50.0")), (2021, Decimal("51.5")), (2022, Decimal("53.2"))],
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
    {
        "code": "NBMS-GBF-RESTORATION-PROGRESS",
        "title": "Restoration Progress in Priority Ecosystems",
        "target_code": "2",
        "framework_indicator_code": "GBF-H5",
        "framework_indicator_title": "Headline Indicator: Restoration progress",
        "indicator_type": NationalIndicatorType.OTHER,
        "coverage_geography": "Priority restoration landscapes",
        "data_points": [(2018, Decimal("12.0")), (2019, Decimal("13.4")), (2020, Decimal("15.2")), (2021, Decimal("16.7")), (2022, Decimal("18.3"))],
    },
    {
        "code": "NBMS-GBF-SPECIES-HABITAT-INDEX",
        "title": "Species Habitat Index",
        "target_code": "4",
        "framework_indicator_code": "GBF-H6",
        "framework_indicator_title": "Headline Indicator: Species habitat index",
        "indicator_type": NationalIndicatorType.HEADLINE,
        "coverage_geography": "Species habitat integrity across priority provinces",
        "data_points": [(2018, Decimal("71.0")), (2019, Decimal("69.8")), (2020, Decimal("68.6")), (2021, Decimal("67.9")), (2022, Decimal("66.8"))],
    },
    {
        "code": "NBMS-GBF-GENETIC-DIVERSITY",
        "title": "Genetic Diversity Retention",
        "target_code": "13",
        "framework_indicator_code": "GBF-H7",
        "framework_indicator_title": "Headline Indicator: Genetic diversity",
        "indicator_type": NationalIndicatorType.BINARY,
        "coverage_geography": "Managed populations and ex situ collections",
        "data_points": [(2018, Decimal("61.0")), (2019, Decimal("61.8")), (2020, Decimal("62.6")), (2021, Decimal("63.9")), (2022, Decimal("64.4"))],
    },
]


def _series_config(code: str) -> dict:
    if code in {"NBMS-GBF-ECOSYSTEM-THREAT", "NBMS-GBF-ECOSYSTEM-PROTECTION"}:
        return {
            "unit": "ecosystems",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "biome": {"type": "string"},
                "ecosystem_type": {"type": "string"},
                "threat_category": {"type": "string"},
                "protection_category": {"type": "string"},
            },
        }
    if code in {"NBMS-GBF-SPECIES-THREAT", "NBMS-GBF-SPECIES-PROTECTION"}:
        return {
            "unit": "species",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "threat_category": {"type": "string"},
                "protection_category": {"type": "string"},
                "taxonomy_kingdom": {"type": "string"},
                "taxonomy_phylum": {"type": "string"},
                "taxonomy_class": {"type": "string"},
                "taxonomy_order": {"type": "string"},
                "taxonomy_family": {"type": "string"},
                "taxonomy_genus": {"type": "string"},
                "taxonomy_species": {"type": "string"},
            },
        }
    if code == "NBMS-GBF-PA-COVERAGE":
        return {
            "unit": "%",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "protected_area_type": {"type": "string"},
                "target_progress": {"type": "string"},
            },
        }
    if code == "NBMS-GBF-IAS-PRESSURE":
        return {
            "unit": "index",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "pathway": {"type": "string"},
                "pressure_category": {"type": "string"},
            },
        }
    if code == "NBMS-GBF-RESTORATION-PROGRESS":
        return {
            "unit": "%",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "biome": {"type": "string"},
                "restoration_status": {"type": "string"},
                "target_progress": {"type": "string"},
            },
        }
    if code == "NBMS-GBF-SPECIES-HABITAT-INDEX":
        return {
            "unit": "index",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "taxonomy_family": {"type": "string"},
                "habitat_index_band": {"type": "string"},
            },
        }
    if code == "NBMS-GBF-GENETIC-DIVERSITY":
        return {
            "unit": "%",
            "disaggregation_schema": {
                "province_code": {"type": "string"},
                "province_name": {"type": "string"},
                "genetic_diversity_band": {"type": "string"},
                "policy_status": {"type": "string"},
            },
        }
    return {
        "unit": "index",
        "disaggregation_schema": {
            "province_code": {"type": "string"},
            "province_name": {"type": "string"},
            "realm": {"type": "string"},
        },
    }


def _point_rows(item: dict) -> list[dict]:
    code = item["code"]
    if code == "NBMS-GBF-ECOSYSTEM-THREAT":
        return [
            {"year": 2022, "value": Decimal("11.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "biome": "Fynbos", "ecosystem_type": "Lowland fynbos", "threat_category": "CR", "protection_category": "LIMITED"}},
            {"year": 2022, "value": Decimal("9.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "biome": "Fynbos", "ecosystem_type": "Mountain fynbos", "threat_category": "EN", "protection_category": "MODERATE"}},
            {"year": 2022, "value": Decimal("8.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "biome": "Savanna", "ecosystem_type": "Subtropical thicket", "threat_category": "VU", "protection_category": "LIMITED"}},
            {"year": 2022, "value": Decimal("6.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "biome": "Grassland", "ecosystem_type": "Moist grassland", "threat_category": "EN", "protection_category": "UNPROTECTED"}},
            {"year": 2021, "value": Decimal("10.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "biome": "Fynbos", "ecosystem_type": "Lowland fynbos", "threat_category": "CR", "protection_category": "LIMITED"}},
            {"year": 2021, "value": Decimal("7.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "biome": "Savanna", "ecosystem_type": "Subtropical thicket", "threat_category": "VU", "protection_category": "MODERATE"}},
        ]
    if code == "NBMS-GBF-ECOSYSTEM-PROTECTION":
        return [
            {"year": 2022, "value": Decimal("16.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "biome": "Fynbos", "ecosystem_type": "Lowland fynbos", "protection_category": "WELL_PROTECTED", "threat_category": "EN"}},
            {"year": 2022, "value": Decimal("12.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "biome": "Savanna", "ecosystem_type": "Albany thicket", "protection_category": "MODERATE", "threat_category": "VU"}},
            {"year": 2022, "value": Decimal("9.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "biome": "Grassland", "ecosystem_type": "Mistbelt grassland", "protection_category": "LIMITED", "threat_category": "EN"}},
            {"year": 2021, "value": Decimal("14.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "biome": "Fynbos", "ecosystem_type": "Lowland fynbos", "protection_category": "WELL_PROTECTED", "threat_category": "EN"}},
        ]
    if code == "NBMS-GBF-SPECIES-THREAT":
        return [
            {"year": 2022, "value": Decimal("12.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "threat_category": "EN", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Mammalia", "taxonomy_order": "Carnivora", "taxonomy_family": "Felidae", "taxonomy_genus": "Panthera", "taxonomy_species": "Panthera pardus"}},
            {"year": 2022, "value": Decimal("9.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "threat_category": "CR", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Mammalia", "taxonomy_order": "Carnivora", "taxonomy_family": "Canidae", "taxonomy_genus": "Lycaon", "taxonomy_species": "Lycaon pictus"}},
            {"year": 2022, "value": Decimal("14.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "threat_category": "VU", "taxonomy_kingdom": "Plantae", "taxonomy_phylum": "Tracheophyta", "taxonomy_class": "Magnoliopsida", "taxonomy_order": "Ericales", "taxonomy_family": "Proteaceae", "taxonomy_genus": "Protea", "taxonomy_species": "Protea roupelliae"}},
            {"year": 2021, "value": Decimal("10.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "threat_category": "EN", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Mammalia", "taxonomy_order": "Carnivora", "taxonomy_family": "Felidae", "taxonomy_genus": "Panthera", "taxonomy_species": "Panthera pardus"}},
        ]
    if code == "NBMS-GBF-SPECIES-PROTECTION":
        return [
            {"year": 2022, "value": Decimal("18.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "protection_category": "WELL_PROTECTED", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Aves", "taxonomy_order": "Accipitriformes", "taxonomy_family": "Accipitridae", "taxonomy_genus": "Aquila", "taxonomy_species": "Aquila verreauxii"}},
            {"year": 2022, "value": Decimal("11.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "protection_category": "LIMITED", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Mammalia", "taxonomy_order": "Primates", "taxonomy_family": "Cercopithecidae", "taxonomy_genus": "Papio", "taxonomy_species": "Papio ursinus"}},
            {"year": 2021, "value": Decimal("15.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "protection_category": "MODERATE", "taxonomy_kingdom": "Animalia", "taxonomy_phylum": "Chordata", "taxonomy_class": "Aves", "taxonomy_order": "Accipitriformes", "taxonomy_family": "Accipitridae", "taxonomy_genus": "Aquila", "taxonomy_species": "Aquila verreauxii"}},
        ]
    if code == "NBMS-GBF-PA-COVERAGE":
        return [
            {"year": 2022, "value": Decimal("18.2"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "protected_area_type": "Formal protected area", "target_progress": "ON_TRACK"}},
            {"year": 2022, "value": Decimal("15.6"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "protected_area_type": "OECM", "target_progress": "ACCELERATE"}},
            {"year": 2022, "value": Decimal("13.4"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "protected_area_type": "Formal protected area", "target_progress": "ACCELERATE"}},
            {"year": 2021, "value": Decimal("17.5"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "protected_area_type": "Formal protected area", "target_progress": "ON_TRACK"}},
        ]
    if code == "NBMS-GBF-IAS-PRESSURE":
        return [
            {"year": 2022, "value": Decimal("64.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "pathway": "ESCAPE", "pressure_category": "HIGH"}},
            {"year": 2022, "value": Decimal("58.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "pathway": "STOWAWAY", "pressure_category": "MEDIUM"}},
            {"year": 2022, "value": Decimal("43.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "pathway": "RELEASE", "pressure_category": "LOW"}},
            {"year": 2021, "value": Decimal("61.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "pathway": "ESCAPE", "pressure_category": "HIGH"}},
        ]
    if code == "NBMS-GBF-RESTORATION-PROGRESS":
        return [
            {"year": 2022, "value": Decimal("28.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "biome": "Fynbos", "restoration_status": "RECOVERING", "target_progress": "ON_TRACK"}},
            {"year": 2022, "value": Decimal("19.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "biome": "Savanna", "restoration_status": "DEGRADED", "target_progress": "OFF_TRACK"}},
            {"year": 2022, "value": Decimal("24.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "biome": "Grassland", "restoration_status": "RESTORED", "target_progress": "ACCELERATE"}},
        ]
    if code == "NBMS-GBF-SPECIES-HABITAT-INDEX":
        return [
            {"year": 2022, "value": Decimal("66.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "taxonomy_family": "Felidae", "habitat_index_band": "MODERATE"}},
            {"year": 2022, "value": Decimal("54.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "taxonomy_family": "Canidae", "habitat_index_band": "LOW"}},
            {"year": 2022, "value": Decimal("72.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "taxonomy_family": "Proteaceae", "habitat_index_band": "HIGH"}},
        ]
    if code == "NBMS-GBF-GENETIC-DIVERSITY":
        return [
            {"year": 2022, "value": Decimal("68.0"), "disaggregation": {"province_code": "WC", "province_name": "Western Cape", "genetic_diversity_band": "STABLE", "policy_status": "Implemented"}},
            {"year": 2022, "value": Decimal("57.0"), "disaggregation": {"province_code": "EC", "province_name": "Eastern Cape", "genetic_diversity_band": "WATCH", "policy_status": "Partial"}},
            {"year": 2022, "value": Decimal("41.0"), "disaggregation": {"province_code": "KZN", "province_name": "KwaZulu-Natal", "genetic_diversity_band": "ERODING", "policy_status": "Emerging"}},
        ]
    return [
        {
            "year": year,
            "value": value,
            "disaggregation": {"province_code": "ALL", "province_name": "National", "realm": "national"},
        }
        for year, value in item["data_points"]
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
        province_units = SpatialUnit.objects.filter(unit_type__code="PROVINCE", is_active=True).order_by("unit_code")
        if province_units.exists():
            programme.coverage_units.set(province_units)

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
                dataset_code=f"DS-{item['code']}",
                defaults={
                    "title": f"Dataset for {item['title']}",
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

            series_config = _series_config(indicator.code)
            series, _ = IndicatorDataSeries.objects.update_or_create(
                indicator=indicator,
                defaults={
                    "series_code": f"SER-{item['code']}",
                    "title": item["title"],
                    "unit": series_config["unit"],
                    "value_type": IndicatorValueType.NUMERIC,
                    "methodology": "Annual aggregated indicator value.",
                    "disaggregation_schema": series_config["disaggregation_schema"],
                    "source_notes": "Seeded for workflow validation and dashboard tests.",
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "export_approved": True,
                },
            )

            for row in _point_rows(item):
                IndicatorDataPoint.objects.update_or_create(
                    series=series,
                    year=row["year"],
                    disaggregation=row["disaggregation"],
                    dataset_release=dataset_release,
                    defaults={
                        "value_numeric": row["value"],
                        "value_text": "",
                        "source_url": "https://www.sanbi.org",
                        "footnote": "Seeded demonstration value.",
                    },
                )

            evidence, _ = Evidence.objects.update_or_create(
                evidence_code=f"EV-{item['code']}",
                defaults={
                    "title": f"Evidence for {item['title']}",
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

            requirement, _ = IndicatorInputRequirement.objects.update_or_create(
                indicator=indicator,
                defaults={
                    "cadence": UpdateFrequency.ANNUAL,
                    "disaggregation_expectations_json": {
                        "province": "recommended",
                        "realm": "recommended",
                        "year": "required",
                    },
                    "notes": "Seeded readiness linkage for spatial and tabular requirements.",
                },
            )

            layer_codes = []
            source_codes = []
            if indicator.code == "NBMS-GBF-PA-COVERAGE":
                layer_codes = ["ZA_PROVINCES_NE", "ZA_PROTECTED_AREAS_NE", "ZA_PROVINCES", "ZA_PROTECTED_AREAS"]
                source_codes = ["NE_ADMIN1_ZA", "NE_PROTECTED_LANDS_ZA"]
            elif indicator.code in {"NBMS-GBF-ECOSYSTEM-THREAT", "NBMS-GBF-ECOSYSTEM-PROTECTION"}:
                layer_codes = ["ZA_ECOSYSTEM_PROXY_NE", "ZA_ECOSYSTEM_THREAT_STATUS", "ZA_PROVINCES"]
                source_codes = ["NE_GEOREGIONS_ZA"]
            elif indicator.code in {"NBMS-GBF-SPECIES-THREAT", "NBMS-GBF-SPECIES-PROTECTION", "NBMS-GBF-IAS-PRESSURE", "NBMS-GBF-RESTORATION-PROGRESS", "NBMS-GBF-SPECIES-HABITAT-INDEX", "NBMS-GBF-GENETIC-DIVERSITY"}:
                layer_codes = ["ZA_PROVINCES_NE", "ZA_PROVINCES"]
                source_codes = ["NE_ADMIN1_ZA"]
            requirement.required_map_layers.set(
                SpatialLayer.objects.filter(layer_code__in=layer_codes).order_by("layer_code", "id")
            )
            requirement.required_map_sources.set(
                SpatialSource.objects.filter(code__in=source_codes).order_by("code", "id")
            )
            requirement.last_checked_at = None
            requirement.save(update_fields=["last_checked_at", "updated_at"])

            method_type = IndicatorMethodType.SPATIAL_OVERLAY if indicator.code == "NBMS-GBF-PA-COVERAGE" else IndicatorMethodType.CSV_IMPORT
            implementation_key = "spatial_overlay_area_by_province" if method_type == IndicatorMethodType.SPATIAL_OVERLAY else "csv_import_aggregation"
            readiness_notes = (
                "Ready when admin boundary and protected area layers are synchronized."
                if method_type == IndicatorMethodType.SPATIAL_OVERLAY
                else "CSV aggregation profile seeded for tabular indicator workflow with indicator-pack drilldowns."
            )
            IndicatorMethodProfile.objects.update_or_create(
                indicator=indicator,
                method_type=method_type,
                implementation_key=implementation_key,
                defaults={
                    "summary": f"Seeded method profile for {indicator.code}.",
                    "required_inputs_json": ["dataset_release", "indicator_data_points"],
                    "disaggregation_requirements_json": ["year", "province"],
                    "readiness_state": IndicatorMethodReadiness.PARTIAL,
                    "readiness_notes": readiness_notes,
                    "source_system": "nbms_seed",
                    "source_ref": "indicator_workflow_v1",
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded indicator workflow pack. Indicators created={created_indicators}, "
                f"total indicators={Indicator.objects.count()}, total GBF targets={len(GBF_TARGETS)}."
            )
        )
