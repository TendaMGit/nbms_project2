from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from nbms_app.models import (
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodProfile,
    IndicatorMethodReadiness,
    IndicatorMethodType,
    IndicatorRegistryCoverageRequirement,
    IndicatorValueType,
    LifecycleStatus,
    MonitoringProgramme,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    QaStatus,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
    SpatialUnitType,
    UpdateFrequency,
)
from nbms_app.services.indicator_method_sdk import run_method_profile


HEADLINE_INDICATORS = [
    ("A.1", "Red list of ecosystems"),
    ("A.2", "Extent of natural ecosystems"),
    ("A.3", "Red list of species"),
    ("A.4", "Genetic diversity within populations of wild species"),
    ("A.5", "Species habitat index"),
    ("B.1", "Services provided by ecosystems"),
    ("B.2", "Sustainable management of wild species"),
    ("B.3", "Green/blue spaces in urban areas"),
    ("B.4", "Benefits from the use of genetic resources"),
    ("C.1", "Monetary benefits from utilization of digital sequence information on genetic resources"),
    (
        "D.1",
        "Public funding, private funding (positive and negative), and private expenditure on conservation and sustainable use of biodiversity",
    ),
    ("D.2", "Domestic public budget on biodiversity"),
    ("D.3", "International public funding and private funding in support of biodiversity"),
]

BINARY_INDICATORS = [
    (1, "National environmental accounting"),
    (2, "Integration of biodiversity into environmental impact assessment and strategic environmental assessment"),
    (
        3,
        "Integration of biodiversity values into policies, planning and development processes",
    ),
    (4, "Biodiversity-inclusive spatial planning"),
    (5, "Biodiversity-relevant taxes"),
    (6, "Incentives positive for biodiversity"),
    (7, "Indicators for sustainable consumption and production patterns"),
    (8, "Trends in biodiversity-friendly and sustainable products"),
    (9, "Participatory integrated biodiversity-inclusive spatial planning and integrated water resources management"),
    (10, "Progress towards sustainable management in agriculture, aquaculture, fisheries and forestry"),
    (11, "Restoration"),
    (12, "Invasive alien species"),
    (13, "Pollution"),
    (14, "Climate change and ocean acidification"),
    (15, "Access to green and blue spaces"),
    (16, "Traditional medicines"),
    (17, "Human-wildlife conflict"),
    (18, "Species management and harvesting"),
    (19, "Sustainable wild meat use"),
    (20, "Urban planning"),
    (21, "Biodiversity in diets"),
    (22, "Mainstreaming gender in biodiversity policy"),
]

TARGET_FOR_GOAL = {
    "A": "2",
    "B": "10",
    "C": "13",
    "D": "19",
}

METHOD_FOR_HEADLINE = {
    "A.1": (IndicatorMethodType.SPATIAL_OVERLAY, "spatial_overlay_area_by_province"),
    "A.2": (IndicatorMethodType.SPATIAL_OVERLAY, "spatial_overlay_area_by_province"),
    "A.3": (IndicatorMethodType.CSV_IMPORT, "csv_import_aggregation"),
    "A.4": (IndicatorMethodType.API_CONNECTOR, "csv_import_aggregation"),
    "A.5": (IndicatorMethodType.API_CONNECTOR, "csv_import_aggregation"),
    "B.1": (IndicatorMethodType.SEEA_ACCOUNTING, "csv_import_aggregation"),
    "B.2": (IndicatorMethodType.CSV_IMPORT, "csv_import_aggregation"),
    "B.3": (IndicatorMethodType.SPATIAL_OVERLAY, "spatial_overlay_area_by_province"),
    "B.4": (IndicatorMethodType.API_CONNECTOR, "csv_import_aggregation"),
    "C.1": (IndicatorMethodType.MANUAL, "csv_import_aggregation"),
    "D.1": (IndicatorMethodType.MANUAL, "csv_import_aggregation"),
    "D.2": (IndicatorMethodType.MANUAL, "csv_import_aggregation"),
    "D.3": (IndicatorMethodType.MANUAL, "csv_import_aggregation"),
}


class Command(BaseCommand):
    help = "Seed COP16/31 GBF headline and binary indicator catalog with method profiles and runnable scaffolds."

    @transaction.atomic
    def handle(self, *args, **options):
        sanbi, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute", "org_type": "Government"},
        )

        framework, _ = Framework.objects.update_or_create(
            code="GBF",
            defaults={
                "title": "Kunming-Montreal Global Biodiversity Framework",
                "description": "GBF monitoring framework seeded from COP16 decision 16/31 Annex I.",
                "organisation": sanbi,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )

        goal_map = {}
        for order, goal_code in enumerate(["A", "B", "C", "D"], start=1):
            goal, _ = FrameworkGoal.objects.update_or_create(
                framework=framework,
                code=goal_code,
                defaults={
                    "title": f"Goal {goal_code}",
                    "description": f"GBF Goal {goal_code}",
                    "sort_order": order,
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "is_active": True,
                },
            )
            goal_map[goal_code] = goal

        target_map = {}
        for i in range(1, 24):
            code = str(i)
            goal_code = "A" if i <= 4 else ("B" if i <= 12 else ("C" if i == 13 else "D"))
            target, _ = FrameworkTarget.objects.update_or_create(
                framework=framework,
                code=code,
                defaults={
                    "goal": goal_map[goal_code],
                    "title": f"GBF Target {code}",
                    "description": f"GBF target {code} (seed scaffold)",
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                },
            )
            target_map[code] = target
            NationalTarget.objects.update_or_create(
                code=f"GBF-T{code}",
                defaults={
                    "title": f"National Target aligned to GBF Target {code}",
                    "description": f"National alignment placeholder for GBF target {code}.",
                    "organisation": sanbi,
                    "responsible_org": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.VALIDATED,
                },
            )

        target_lookup = {target.code.replace("GBF-T", ""): target for target in NationalTarget.objects.filter(code__startswith="GBF-T")}

        runnable_profiles = []

        for code, title in HEADLINE_INDICATORS:
            compact = code.replace(".", "")
            goal_code = code[0]
            target_code = TARGET_FOR_GOAL[goal_code]
            method_type, implementation_key = METHOD_FOR_HEADLINE[code]
            framework_indicator, _ = FrameworkIndicator.objects.update_or_create(
                framework=framework,
                code=f"GBF-H-{compact}",
                defaults={
                    "title": title,
                    "description": f"GBF headline indicator {code}",
                    "indicator_type": FrameworkIndicatorType.HEADLINE,
                    "framework_target": target_map[target_code],
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                },
            )
            indicator, _ = Indicator.objects.update_or_create(
                code=f"GBF-H-{compact}-ZA",
                defaults={
                    "title": title,
                    "national_target": target_lookup[target_code],
                    "indicator_type": NationalIndicatorType.HEADLINE,
                    "reporting_cadence": UpdateFrequency.ANNUAL,
                    "qa_status": QaStatus.VALIDATED,
                    "reporting_capability": "partial",
                    "owner_organisation": sanbi,
                    "responsible_org": sanbi,
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "coverage_geography": "South Africa",
                    "coverage_time_start_year": 2018,
                    "coverage_time_end_year": 2024,
                    "computation_notes": f"COP16/31 headline indicator {code}.",
                    "last_updated_on": date(2025, 12, 31),
                },
            )
            IndicatorFrameworkIndicatorLink.objects.update_or_create(
                indicator=indicator,
                framework_indicator=framework_indicator,
                defaults={"relation_type": "primary", "confidence": 95, "is_active": True},
            )
            profile, _ = IndicatorMethodProfile.objects.update_or_create(
                indicator=indicator,
                method_type=method_type,
                implementation_key=implementation_key,
                defaults={
                    "summary": f"Primary computation profile for headline indicator {code}.",
                    "required_inputs_json": ["indicator_series", "metadata", "qa_checks"],
                    "disaggregation_requirements_json": ["year", "geography", "sex", "ecosystem_type"],
                    "readiness_state": IndicatorMethodReadiness.PARTIAL,
                    "readiness_notes": "Seeded scaffold awaiting validated data feeds.",
                    "source_system": "COP16/31",
                    "source_ref": code,
                    "is_active": True,
                },
            )
            runnable_profiles.append(profile)

            if method_type == IndicatorMethodType.CSV_IMPORT:
                series, _ = IndicatorDataSeries.objects.update_or_create(
                    series_code=f"SER-{indicator.code}",
                    defaults={
                        "indicator": indicator,
                        "title": f"{indicator.code} annual series",
                        "unit": "index",
                        "value_type": IndicatorValueType.NUMERIC,
                        "status": LifecycleStatus.PUBLISHED,
                        "sensitivity": SensitivityLevel.PUBLIC,
                        "organisation": sanbi,
                        "methodology": "Seeded annual indicator series.",
                    },
                )
                for year, value in [(2020, Decimal("48.2")), (2021, Decimal("49.1")), (2022, Decimal("50.7")), (2023, Decimal("51.4"))]:
                    IndicatorDataPoint.objects.update_or_create(
                        series=series,
                        year=year,
                        defaults={"value_numeric": value, "disaggregation": {"geography": "national"}},
                    )

            if method_type == IndicatorMethodType.SPATIAL_OVERLAY:
                province_unit_type = SpatialUnitType.objects.filter(code="PROVINCE").first()
                layer, _ = SpatialLayer.objects.update_or_create(
                    layer_code=f"GBF_{compact}_LAYER",
                    defaults={
                        "title": f"{indicator.code} spatial layer",
                        "name": f"{indicator.code} spatial layer",
                        "slug": f"gbf-h-{compact.lower()}-layer",
                        "source_type": SpatialLayerSourceType.NBMS_TABLE,
                        "data_ref": "nbms_app_spatialfeature",
                        "sensitivity": SensitivityLevel.PUBLIC,
                        "is_public": True,
                        "indicator": indicator,
                        "theme": "GBF",
                        "default_style_json": {"fillColor": "#238b45", "fillOpacity": 0.4},
                    },
                )
                SpatialFeature.objects.update_or_create(
                    layer=layer,
                    feature_key=f"{compact}-WC",
                    defaults={
                        "feature_id": f"{compact}-WC",
                        "province_code": "WC",
                        "year": 2023,
                        "indicator": indicator,
                        "name": f"{indicator.code} Western Cape",
                        "properties": {"area_ha": 14523.4},
                        "properties_json": {"area_ha": 14523.4},
                        "geometry_json": {
                            "type": "Polygon",
                            "coordinates": [[[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]],
                        },
                    },
                )
                IndicatorDataSeries.objects.update_or_create(
                    series_code=f"SER-{indicator.code}",
                    defaults={
                        "indicator": indicator,
                        "title": f"{indicator.code} spatial overlay series",
                        "unit": "ha",
                        "value_type": IndicatorValueType.NUMERIC,
                        "status": LifecycleStatus.PUBLISHED,
                        "sensitivity": SensitivityLevel.PUBLIC,
                        "organisation": sanbi,
                        "methodology": "Spatial overlay by province.",
                        "spatial_layer": layer,
                        "spatial_unit_type": province_unit_type,
                        "spatial_resolution": "province",
                    },
                )

        for number, title in BINARY_INDICATORS:
            code = f"{number:02d}"
            framework_indicator, _ = FrameworkIndicator.objects.update_or_create(
                framework=framework,
                code=f"GBF-BI-{code}",
                defaults={
                    "title": title,
                    "description": f"GBF binary indicator {number}",
                    "indicator_type": FrameworkIndicatorType.BINARY,
                    "framework_target": target_map[str(min(number, 22))],
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                },
            )
            indicator, _ = Indicator.objects.update_or_create(
                code=f"GBF-BI-{code}-ZA",
                defaults={
                    "title": title,
                    "national_target": target_lookup[str(min(number, 22))],
                    "indicator_type": NationalIndicatorType.BINARY,
                    "reporting_cadence": UpdateFrequency.ANNUAL,
                    "qa_status": QaStatus.VALIDATED,
                    "reporting_capability": "partial",
                    "owner_organisation": sanbi,
                    "responsible_org": sanbi,
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "coverage_geography": "South Africa",
                    "coverage_time_start_year": 2020,
                    "coverage_time_end_year": 2024,
                    "computation_notes": f"COP16/31 binary indicator {number}.",
                    "last_updated_on": date(2025, 12, 31),
                },
            )
            IndicatorFrameworkIndicatorLink.objects.update_or_create(
                indicator=indicator,
                framework_indicator=framework_indicator,
                defaults={"relation_type": "primary", "confidence": 90, "is_active": True},
            )
            profile, _ = IndicatorMethodProfile.objects.update_or_create(
                indicator=indicator,
                method_type=IndicatorMethodType.BINARY_QUESTIONNAIRE,
                implementation_key="binary_questionnaire_aggregator",
                defaults={
                    "summary": f"Binary questionnaire aggregation profile for indicator {number}.",
                    "required_inputs_json": ["binary_questionnaire_responses"],
                    "disaggregation_requirements_json": ["reporting_cycle", "responsible_institution"],
                    "readiness_state": IndicatorMethodReadiness.PARTIAL,
                    "readiness_notes": "Ready for questionnaire response ingestion.",
                    "source_system": "COP16/31",
                    "source_ref": str(number),
                    "is_active": True,
                },
            )
            runnable_profiles.append(profile)

        # Ensure all method types are represented at least once for catalogue readiness.
        anchor_indicator = Indicator.objects.filter(code__startswith="GBF-H-").order_by("code").first()
        if anchor_indicator:
            for method_type, impl in [
                (IndicatorMethodType.SCRIPTED_PYTHON, "scripted_python_stub"),
                (IndicatorMethodType.SCRIPTED_R_CONTAINER, "scripted_r_container_stub"),
            ]:
                IndicatorMethodProfile.objects.update_or_create(
                    indicator=anchor_indicator,
                    method_type=method_type,
                    implementation_key=impl,
                    defaults={
                        "summary": f"Scaffold profile for {method_type} execution.",
                        "required_inputs_json": ["methodology_version", "input_dataset_manifest"],
                        "disaggregation_requirements_json": ["year"],
                        "readiness_state": IndicatorMethodReadiness.BLOCKED,
                        "readiness_notes": "Scaffold defined; implementation pending.",
                        "is_active": True,
                    },
                )

        # Promote three GBF indicators to explicit registry-consuming methods.
        ecosystem_indicator = Indicator.objects.filter(code="GBF-H-A1-ZA").first()
        species_indicator = Indicator.objects.filter(code="GBF-H-A3-ZA").first()
        ias_indicator = Indicator.objects.filter(code="GBF-BI-12-ZA").first()
        registry_profiles = []
        if ecosystem_indicator:
            profile, _ = IndicatorMethodProfile.objects.update_or_create(
                indicator=ecosystem_indicator,
                method_type=IndicatorMethodType.SCRIPTED_PYTHON,
                implementation_key="ecosystem_registry_summary",
                defaults={
                    "summary": "Consumes ecosystem registry marts for ecosystem extent/protection signal.",
                    "required_inputs_json": ["ecosystem_gold_summary"],
                    "disaggregation_requirements_json": ["province", "biome", "bioregion"],
                    "readiness_state": IndicatorMethodReadiness.PARTIAL,
                    "readiness_notes": "Requires refreshed ecosystem registry marts.",
                    "source_system": "nbms.phase11",
                    "source_ref": "ecosystem_registry_summary",
                    "is_active": True,
                },
            )
            registry_profiles.append(profile)
            IndicatorRegistryCoverageRequirement.objects.update_or_create(
                indicator=ecosystem_indicator,
                defaults={
                    "require_ecosystem_registry": True,
                    "require_taxon_registry": False,
                    "require_ias_registry": False,
                    "min_ecosystem_count": 1,
                    "notes": "Requires ecosystem registry coverage for ecosystem indicator readiness.",
                },
            )
        if species_indicator:
            profile, _ = IndicatorMethodProfile.objects.update_or_create(
                indicator=species_indicator,
                method_type=IndicatorMethodType.SCRIPTED_PYTHON,
                implementation_key="taxon_registry_native_voucher_ratio",
                defaults={
                    "summary": "Consumes taxon registry marts for species/population readiness signal.",
                    "required_inputs_json": ["taxon_gold_summary"],
                    "disaggregation_requirements_json": ["rank", "native", "voucher"],
                    "readiness_state": IndicatorMethodReadiness.PARTIAL,
                    "readiness_notes": "Requires refreshed taxon registry marts.",
                    "source_system": "nbms.phase11",
                    "source_ref": "taxon_registry_native_voucher_ratio",
                    "is_active": True,
                },
            )
            registry_profiles.append(profile)
            IndicatorRegistryCoverageRequirement.objects.update_or_create(
                indicator=species_indicator,
                defaults={
                    "require_ecosystem_registry": False,
                    "require_taxon_registry": True,
                    "require_ias_registry": False,
                    "min_taxon_count": 1,
                    "notes": "Requires taxon registry coverage for species indicator readiness.",
                },
            )
        if ias_indicator:
            profile, _ = IndicatorMethodProfile.objects.update_or_create(
                indicator=ias_indicator,
                method_type=IndicatorMethodType.SCRIPTED_PYTHON,
                implementation_key="ias_registry_pressure_index",
                defaults={
                    "summary": "Consumes IAS registry marts for Target 6 pressure signal.",
                    "required_inputs_json": ["ias_gold_summary"],
                    "disaggregation_requirements_json": ["habitat", "pathway", "eicat", "seicat"],
                    "readiness_state": IndicatorMethodReadiness.PARTIAL,
                    "readiness_notes": "Requires refreshed IAS registry marts.",
                    "source_system": "nbms.phase11",
                    "source_ref": "ias_registry_pressure_index",
                    "is_active": True,
                },
            )
            registry_profiles.append(profile)
            IndicatorRegistryCoverageRequirement.objects.update_or_create(
                indicator=ias_indicator,
                defaults={
                    "require_ecosystem_registry": False,
                    "require_taxon_registry": False,
                    "require_ias_registry": True,
                    "min_ias_count": 1,
                    "notes": "Requires IAS registry coverage for Target 6 readiness.",
                },
            )

        # Trigger real compute paths for at least three seeded profiles.
        for profile in runnable_profiles[:3]:
            run_method_profile(profile=profile, user=None, params={"seeded": True}, use_cache=False)
        for profile in registry_profiles:
            run_method_profile(profile=profile, user=None, params={"seeded": True}, use_cache=False)

        monitoring_programme = MonitoringProgramme.objects.filter(programme_code="NBMS-CORE-PROGRAMME").first()
        if monitoring_programme:
            for indicator in Indicator.objects.filter(code__startswith="GBF-").order_by("code")[:30]:
                monitoring_programme.indicator_links.update_or_create(
                    indicator=indicator,
                    defaults={"relationship_type": "supporting", "role": "gbf_catalog_seed", "is_active": True},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded GBF catalog: {len(HEADLINE_INDICATORS)} headline and {len(BINARY_INDICATORS)} binary indicators."
            )
        )
