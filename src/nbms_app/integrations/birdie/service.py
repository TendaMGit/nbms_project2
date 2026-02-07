from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction

from nbms_app.integrations.birdie.client import BirdieClient
from nbms_app.models import (
    BirdieModelOutput,
    BirdieSite,
    BirdieSpecies,
    Framework,
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
    IndicatorValueType,
    IntegrationDataAsset,
    IntegrationDataLayer,
    LifecycleStatus,
    MonitoringProgramme,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    ProgrammeIndicatorLink,
    ProgrammeRefreshCadence,
    QaStatus,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
    UpdateFrequency,
)


BIRDIE_INDICATOR_SPECS = [
    {
        "code": "BIRDIE-WATERBIRD-ABUNDANCE-ZA",
        "title": "Waterbird Abundance Trend",
        "metric_code": "waterbird_abundance_trend",
        "target_code": "2",
        "description": "State-space trend index aggregated from BIRDIE site-level abundance outputs.",
    },
    {
        "code": "BIRDIE-SPECIES-RICHNESS-ZA",
        "title": "Waterbird Species Richness Trend",
        "metric_code": "species_richness_trend",
        "target_code": "4",
        "description": "Species richness trend derived from BIRDIE site-by-year species observations.",
    },
    {
        "code": "BIRDIE-OCCUPANCY-SIGNAL-ZA",
        "title": "Waterbird Occupancy Change Signal",
        "metric_code": "occupancy_change_signal",
        "target_code": "1",
        "description": "Occupancy probability change signals from BIRDIE pentad/site prediction outputs.",
    },
    {
        "code": "BIRDIE-WCV-SCORE-ZA",
        "title": "Waterbird Conservation Value Score",
        "metric_code": "waterbird_conservation_value",
        "target_code": "3",
        "description": "Wetland waterbird conservation value category and score.",
    },
]


def _payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _upsert_integration_asset(*, layer, dataset_key, record_key, payload, endpoint):
    IntegrationDataAsset.objects.update_or_create(
        source_system="BIRDIE",
        layer=layer,
        dataset_key=dataset_key,
        record_key=record_key,
        defaults={
            "payload_json": payload,
            "payload_hash": _payload_hash(payload),
            "source_endpoint": endpoint,
            "source_version": str(payload.get("model_version", "")) if isinstance(payload, dict) else "",
            "is_restricted": False,
        },
    )


def _get_or_create_org():
    return Organisation.objects.get_or_create(
        org_code="SANBI",
        defaults={"name": "South African National Biodiversity Institute", "org_type": "Government"},
    )[0]


def _get_or_create_framework_target(framework, code):
    return FrameworkTarget.objects.get_or_create(
        framework=framework,
        code=code,
        defaults={
            "title": f"GBF Target {code}",
            "description": f"BIRDIE indicator alignment target {code}.",
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
        },
    )[0]


def _get_or_create_national_target(*, org, code):
    return NationalTarget.objects.get_or_create(
        code=code,
        defaults={
            "title": f"National Target {code}",
            "description": "National target for wetland and waterbird monitoring integration.",
            "responsible_org": org,
            "qa_status": QaStatus.VALIDATED,
            "reporting_cadence": UpdateFrequency.ANNUAL,
            "organisation": org,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
        },
    )[0]


@transaction.atomic
def ingest_birdie_snapshot(*, actor=None):
    client = BirdieClient()
    source_meta = {
        "source": "BIRDIE",
        "fetched_at": date.today().isoformat(),
    }
    species_rows = client.fetch_species_list()
    site_rows = client.fetch_site_list()
    abundance_rows = client.fetch_abundance_trends()
    occupancy_rows = client.fetch_occupancy_predictions()
    wcv_rows = client.fetch_wcv_scores()

    _upsert_integration_asset(
        layer=IntegrationDataLayer.BRONZE,
        dataset_key="species",
        record_key="snapshot",
        payload={"rows": species_rows, **source_meta},
        endpoint="species",
    )
    _upsert_integration_asset(
        layer=IntegrationDataLayer.BRONZE,
        dataset_key="sites",
        record_key="snapshot",
        payload={"rows": site_rows, **source_meta},
        endpoint="sites",
    )
    _upsert_integration_asset(
        layer=IntegrationDataLayer.BRONZE,
        dataset_key="abundance_trends",
        record_key="snapshot",
        payload={"rows": abundance_rows, **source_meta},
        endpoint="abundance_trends",
    )
    _upsert_integration_asset(
        layer=IntegrationDataLayer.BRONZE,
        dataset_key="occupancy_predictions",
        record_key="snapshot",
        payload={"rows": occupancy_rows, **source_meta},
        endpoint="occupancy_predictions",
    )
    _upsert_integration_asset(
        layer=IntegrationDataLayer.BRONZE,
        dataset_key="wcv_scores",
        record_key="snapshot",
        payload={"rows": wcv_rows, **source_meta},
        endpoint="wcv_scores",
    )

    species_lookup = {}
    for row in species_rows:
        species, _ = BirdieSpecies.objects.update_or_create(
            species_code=row["species_code"],
            defaults={
                "common_name": row.get("common_name", row["species_code"]),
                "scientific_name": row.get("scientific_name", ""),
                "guild": row.get("guild", ""),
                "metadata_json": row,
                "source_ref": "BIRDIE",
                "is_restricted": False,
            },
        )
        species_lookup[species.species_code] = species
        _upsert_integration_asset(
            layer=IntegrationDataLayer.SILVER,
            dataset_key="species",
            record_key=species.species_code,
            payload=row,
            endpoint="species",
        )

    site_lookup = {}
    for row in site_rows:
        site, _ = BirdieSite.objects.update_or_create(
            site_code=row["site_code"],
            defaults={
                "site_name": row.get("site_name", row["site_code"]),
                "province_code": row.get("province_code", ""),
                "convention_type": row.get("convention_type", ""),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "metadata_json": row,
                "is_restricted": False,
            },
        )
        site_lookup[site.site_code] = site
        _upsert_integration_asset(
            layer=IntegrationDataLayer.SILVER,
            dataset_key="sites",
            record_key=site.site_code,
            payload=row,
            endpoint="sites",
        )

    org = _get_or_create_org()
    framework, _ = Framework.objects.get_or_create(
        code="GBF",
        defaults={
            "title": "Kunming-Montreal Global Biodiversity Framework",
            "description": "Global Biodiversity Framework",
            "organisation": org,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
        },
    )

    indicator_lookup = {}
    for spec in BIRDIE_INDICATOR_SPECS:
        national_target = _get_or_create_national_target(org=org, code=f"BIRDIE-{spec['target_code']}")
        indicator, _ = Indicator.objects.update_or_create(
            code=spec["code"],
            defaults={
                "title": spec["title"],
                "national_target": national_target,
                "indicator_type": NationalIndicatorType.COMPONENT,
                "reporting_cadence": UpdateFrequency.ANNUAL,
                "qa_status": QaStatus.VALIDATED,
                "reporting_capability": "partial",
                "responsible_org": org,
                "owner_organisation": org,
                "organisation": org,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
                "coverage_geography": "South Africa",
                "coverage_time_start_year": 2021,
                "coverage_time_end_year": 2023,
                "computation_notes": spec["description"],
                "last_updated_on": date(2025, 12, 31),
            },
        )
        target = _get_or_create_framework_target(framework, spec["target_code"])
        framework_indicator, _ = FrameworkIndicator.objects.update_or_create(
            framework=framework,
            code=f"{spec['code']}-FW",
            defaults={
                "title": spec["title"],
                "description": spec["description"],
                "indicator_type": FrameworkIndicatorType.COMPONENT,
                "framework_target": target,
                "organisation": org,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
            },
        )
        IndicatorFrameworkIndicatorLink.objects.update_or_create(
            indicator=indicator,
            framework_indicator=framework_indicator,
            defaults={"relation_type": "derived", "confidence": 90, "is_active": True},
        )
        IndicatorMethodProfile.objects.update_or_create(
            indicator=indicator,
            method_type=IndicatorMethodType.API_CONNECTOR,
            implementation_key="birdie_api_connector",
            defaults={
                "summary": "BIRDIE API connector ingestion and aggregation pathway.",
                "required_inputs_json": ["birdie_site_outputs", "species_metadata"],
                "disaggregation_requirements_json": ["year", "province", "site_code", "species"],
                "readiness_state": IndicatorMethodReadiness.PARTIAL,
                "readiness_notes": "Connected to BIRDIE snapshot ingest.",
                "source_system": "BIRDIE",
                "source_ref": spec["metric_code"],
                "is_active": True,
            },
        )
        indicator_lookup[spec["metric_code"]] = indicator

    def _upsert_output(metric_code, row, value_numeric=None, value_text="", value_json=None):
        site = site_lookup.get(row.get("site_code"))
        species = species_lookup.get(row.get("species_code"))
        indicator = indicator_lookup.get(metric_code)
        output, _ = BirdieModelOutput.objects.update_or_create(
            metric_code=metric_code,
            site=site,
            species=species,
            year=int(row["year"]),
            defaults={
                "indicator": indicator,
                "value_numeric": value_numeric,
                "value_text": value_text,
                "value_json": value_json or {},
                "model_version": row.get("model_version", ""),
                "provenance_json": {"source": "BIRDIE", "raw": row},
                "is_restricted": False,
            },
        )
        _upsert_integration_asset(
            layer=IntegrationDataLayer.GOLD,
            dataset_key=metric_code,
            record_key=f"{row.get('site_code', 'NA')}:{row.get('species_code', 'NA')}:{row['year']}",
            payload={
                "metric_code": metric_code,
                "site_code": row.get("site_code"),
                "species_code": row.get("species_code"),
                "year": row["year"],
                "value_numeric": str(value_numeric) if value_numeric is not None else "",
                "value_text": value_text,
                "value_json": value_json or {},
            },
            endpoint=metric_code,
        )
        return output

    for row in abundance_rows:
        _upsert_output(
            "waterbird_abundance_trend",
            row,
            value_numeric=Decimal(str(row.get("value") or 0)),
            value_json={"site_code": row.get("site_code"), "species_code": row.get("species_code")},
        )

    occupancy_by_species = defaultdict(lambda: defaultdict(list))
    for row in occupancy_rows:
        psi_value = Decimal(str(row.get("psi") or 0))
        _upsert_output(
            "occupancy_change_signal",
            row,
            value_numeric=psi_value,
            value_json={"site_code": row.get("site_code"), "species_code": row.get("species_code"), "psi": float(psi_value)},
        )
        occupancy_by_species[row.get("species_code")][int(row["year"])].append(float(psi_value))

    richness_by_site_year = defaultdict(set)
    for row in abundance_rows:
        richness_by_site_year[(row.get("site_code"), int(row["year"]))].add(row.get("species_code"))
    for (site_code, year), species_codes in richness_by_site_year.items():
        _upsert_output(
            "species_richness_trend",
            {"site_code": site_code, "year": year},
            value_numeric=Decimal(str(len(species_codes))),
            value_json={"species_codes": sorted(species_codes)},
        )

    for row in wcv_rows:
        _upsert_output(
            "waterbird_conservation_value",
            row,
            value_numeric=Decimal(str(row.get("value") or 0)),
            value_text=row.get("category", ""),
            value_json={"category": row.get("category", "")},
        )

    programme, _ = MonitoringProgramme.objects.update_or_create(
        programme_code="NBMS-BIRDIE-INTEGRATION",
        defaults={
            "title": "BIRDIE Waterbird Integration Programme",
            "description": "Integration pipeline for BIRDIE wetlands and waterbird outputs.",
            "programme_type": "national",
            "lead_org": org,
            "refresh_cadence": ProgrammeRefreshCadence.MONTHLY,
            "scheduler_enabled": True,
            "pipeline_definition_json": {
                "steps": [
                    {"key": "ingest", "type": "ingest"},
                    {"key": "validate", "type": "validate"},
                    {"key": "compute", "type": "compute"},
                    {"key": "publish", "type": "publish"},
                ],
                "source_system": "BIRDIE",
            },
            "data_quality_rules_json": {"minimum_dataset_links": 0, "minimum_indicator_links": 4},
            "lineage_notes": "Bronze/Silver/Gold lineage stored in IntegrationDataAsset.",
            "is_active": True,
            "source_system": "BIRDIE",
            "source_ref": "birdie_api",
        },
    )
    for spec in BIRDIE_INDICATOR_SPECS:
        indicator = indicator_lookup[spec["metric_code"]]
        ProgrammeIndicatorLink.objects.update_or_create(
            programme=programme,
            indicator=indicator,
            defaults={"relationship_type": "supporting", "role": "birdie_feed", "is_active": True},
        )

    series_map = {}
    for spec in BIRDIE_INDICATOR_SPECS:
        indicator = indicator_lookup[spec["metric_code"]]
        series, _ = IndicatorDataSeries.objects.update_or_create(
            indicator=indicator,
            title=f"{indicator.code} annual series",
            defaults={
                "unit": "index",
                "value_type": IndicatorValueType.NUMERIC,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
                "organisation": org,
                "methodology": "Derived from BIRDIE ingestion feed.",
            },
        )
        series_map[spec["metric_code"]] = series

    aggregates = defaultdict(lambda: defaultdict(list))
    for item in BirdieModelOutput.objects.filter(metric_code__in=[spec["metric_code"] for spec in BIRDIE_INDICATOR_SPECS]):
        if item.value_numeric is not None:
            aggregates[item.metric_code][item.year].append(float(item.value_numeric))

    for metric_code, year_map in aggregates.items():
        series = series_map[metric_code]
        for year, values in sorted(year_map.items()):
            numeric_mean = Decimal(str(round(sum(values) / len(values), 6)))
            IndicatorDataPoint.objects.update_or_create(
                series=series,
                year=year,
                defaults={"value_numeric": numeric_mean, "disaggregation": {"geography": "national", "source": "BIRDIE"}},
            )

    occupancy_layer, _ = SpatialLayer.objects.update_or_create(
        slug="birdie-occupancy-sites",
        defaults={
            "name": "BIRDIE Occupancy Predictions",
            "description": "Site-level occupancy prediction signals from BIRDIE.",
            "source_type": SpatialLayerSourceType.INDICATOR,
            "sensitivity": SensitivityLevel.PUBLIC,
            "is_public": True,
            "indicator": indicator_lookup["occupancy_change_signal"],
            "default_style_json": {"circleColor": "#2f8f67", "circleRadius": 6, "circleOpacity": 0.8},
        },
    )
    for row in occupancy_rows:
        site = site_lookup.get(row.get("site_code"))
        if not site or site.longitude is None or site.latitude is None:
            continue
        eps = 0.12
        x = float(site.longitude)
        y = float(site.latitude)
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [x - eps, y - eps],
                    [x + eps, y - eps],
                    [x + eps, y + eps],
                    [x - eps, y + eps],
                    [x - eps, y - eps],
                ]
            ],
        }
        SpatialFeature.objects.update_or_create(
            layer=occupancy_layer,
            feature_key=f"{site.site_code}:{row.get('species_code')}:{row.get('year')}",
            defaults={
                "name": f"{site.site_name} {row.get('species_code')} {row.get('year')}",
                "province_code": site.province_code,
                "year": int(row["year"]),
                "indicator": indicator_lookup["occupancy_change_signal"],
                "properties_json": {
                    "site_code": site.site_code,
                    "species_code": row.get("species_code"),
                    "psi": row.get("psi"),
                },
                "geometry_json": geometry,
            },
        )

    return {
        "species_count": len(species_rows),
        "site_count": len(site_rows),
        "abundance_row_count": len(abundance_rows),
        "occupancy_row_count": len(occupancy_rows),
        "wcv_row_count": len(wcv_rows),
        "programme_code": programme.programme_code,
        "indicator_codes": sorted(spec["code"] for spec in BIRDIE_INDICATOR_SPECS),
    }
