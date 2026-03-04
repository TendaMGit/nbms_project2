from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Evidence,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    LifecycleStatus,
    NationalTargetFrameworkTargetLink,
    SensitivityLevel,
    SpatialLayer,
    SpatialUnit,
    SpatialUnitType,
)


DEMO_RELEASE_DATE = date(2024, 12, 31)
DEMO_RELEASE_VERSION = "demo-analytics-v1"
DEMO_POINT_FOOTNOTE = "Seeded approved analytics demonstration value."
PROVINCE_LAYER_CODES = ["ZA_PROVINCES", "ZA_PROVINCES_NE"]

DEMO_INDICATOR_CODES = [
    "NBMS-GBF-ECOSYSTEM-EXTENT",
    "NBMS-GBF-ECOSYSTEM-THREAT",
    "NBMS-GBF-ECOSYSTEM-PROTECTION",
    "NBMS-GBF-SPECIES-THREAT",
    "NBMS-GBF-SPECIES-PROTECTION",
    "NBMS-GBF-PA-COVERAGE",
    "NBMS-GBF-IAS-PRESSURE",
    "NBMS-GBF-RESTORATION-PROGRESS",
    "NBMS-GBF-SPECIES-HABITAT-INDEX",
    "NBMS-GBF-GENETIC-DIVERSITY",
]

PROVINCES = [
    {"code": "EC", "name": "Eastern Cape", "biome": "Albany Thicket", "biome_code": "THI"},
    {"code": "FS", "name": "Free State", "biome": "Grassland", "biome_code": "GRA"},
    {"code": "GP", "name": "Gauteng", "biome": "Grassland", "biome_code": "GRA"},
    {"code": "KZN", "name": "KwaZulu-Natal", "biome": "Grassland", "biome_code": "GRA"},
    {"code": "LP", "name": "Limpopo", "biome": "Savanna", "biome_code": "SAV"},
    {"code": "MP", "name": "Mpumalanga", "biome": "Savanna", "biome_code": "SAV"},
    {"code": "NC", "name": "Northern Cape", "biome": "Succulent Karoo", "biome_code": "SUK"},
    {"code": "NW", "name": "North West", "biome": "Savanna", "biome_code": "SAV"},
    {"code": "WC", "name": "Western Cape", "biome": "Fynbos", "biome_code": "FYN"},
]

TAXONOMY_THREAT_ROWS = [
    {
        "province_code": "WC",
        "province_name": "Western Cape",
        "threat_category": "CR",
        "threat_category_label": "Critically endangered",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Amphibia",
        "taxonomy_order": "Anura",
        "taxonomy_family": "Heleophrynidae",
        "taxonomy_genus": "Heleophryne",
        "taxonomy_species": "Heleophryne rosei",
    },
    {
        "province_code": "EC",
        "province_name": "Eastern Cape",
        "threat_category": "EN",
        "threat_category_label": "Endangered",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Aves",
        "taxonomy_order": "Gruiformes",
        "taxonomy_family": "Gruidae",
        "taxonomy_genus": "Balearica",
        "taxonomy_species": "Balearica regulorum",
    },
    {
        "province_code": "KZN",
        "province_name": "KwaZulu-Natal",
        "threat_category": "CR",
        "threat_category_label": "Critically endangered",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Amphibia",
        "taxonomy_order": "Anura",
        "taxonomy_family": "Pyxicephalidae",
        "taxonomy_genus": "Cacosternum",
        "taxonomy_species": "Cacosternum nanum",
    },
    {
        "province_code": "GP",
        "province_name": "Gauteng",
        "threat_category": "VU",
        "threat_category_label": "Vulnerable",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Mammalia",
        "taxonomy_order": "Carnivora",
        "taxonomy_family": "Felidae",
        "taxonomy_genus": "Panthera",
        "taxonomy_species": "Panthera pardus",
    },
    {
        "province_code": "FS",
        "province_name": "Free State",
        "threat_category": "EN",
        "threat_category_label": "Endangered",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Mammalia",
        "taxonomy_order": "Carnivora",
        "taxonomy_family": "Canidae",
        "taxonomy_genus": "Lycaon",
        "taxonomy_species": "Lycaon pictus",
    },
    {
        "province_code": "LP",
        "province_name": "Limpopo",
        "threat_category": "VU",
        "threat_category_label": "Vulnerable",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Aves",
        "taxonomy_order": "Accipitriformes",
        "taxonomy_family": "Accipitridae",
        "taxonomy_genus": "Aquila",
        "taxonomy_species": "Aquila verreauxii",
    },
    {
        "province_code": "MP",
        "province_name": "Mpumalanga",
        "threat_category": "EN",
        "threat_category_label": "Endangered",
        "taxonomy_kingdom": "Plantae",
        "taxonomy_phylum": "Tracheophyta",
        "taxonomy_class": "Magnoliopsida",
        "taxonomy_order": "Ericales",
        "taxonomy_family": "Proteaceae",
        "taxonomy_genus": "Protea",
        "taxonomy_species": "Protea roupelliae",
    },
    {
        "province_code": "NW",
        "province_name": "North West",
        "threat_category": "NT",
        "threat_category_label": "Near threatened",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Reptilia",
        "taxonomy_order": "Testudines",
        "taxonomy_family": "Testudinidae",
        "taxonomy_genus": "Stigmochelys",
        "taxonomy_species": "Stigmochelys pardalis",
    },
    {
        "province_code": "NC",
        "province_name": "Northern Cape",
        "threat_category": "EN",
        "threat_category_label": "Endangered",
        "taxonomy_kingdom": "Plantae",
        "taxonomy_phylum": "Tracheophyta",
        "taxonomy_class": "Magnoliopsida",
        "taxonomy_order": "Asterales",
        "taxonomy_family": "Asteraceae",
        "taxonomy_genus": "Arctotis",
        "taxonomy_species": "Arctotis venusta",
    },
]

TAXONOMY_PROTECTION_ROWS = [
    {
        "province_code": "WC",
        "province_name": "Western Cape",
        "protection_category": "WELL_PROTECTED",
        "protection_category_label": "Well protected",
        "taxonomy_kingdom": "Plantae",
        "taxonomy_phylum": "Tracheophyta",
        "taxonomy_class": "Magnoliopsida",
        "taxonomy_order": "Proteales",
        "taxonomy_family": "Proteaceae",
        "taxonomy_genus": "Leucospermum",
        "taxonomy_species": "Leucospermum conocarpodendron",
    },
    {
        "province_code": "EC",
        "province_name": "Eastern Cape",
        "protection_category": "LIMITED",
        "protection_category_label": "Limited protection",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Mammalia",
        "taxonomy_order": "Primates",
        "taxonomy_family": "Cercopithecidae",
        "taxonomy_genus": "Papio",
        "taxonomy_species": "Papio ursinus",
    },
    {
        "province_code": "KZN",
        "province_name": "KwaZulu-Natal",
        "protection_category": "MODERATE",
        "protection_category_label": "Moderately protected",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Aves",
        "taxonomy_order": "Accipitriformes",
        "taxonomy_family": "Accipitridae",
        "taxonomy_genus": "Aquila",
        "taxonomy_species": "Aquila verreauxii",
    },
    {
        "province_code": "GP",
        "province_name": "Gauteng",
        "protection_category": "MODERATE",
        "protection_category_label": "Moderately protected",
        "taxonomy_kingdom": "Plantae",
        "taxonomy_phylum": "Tracheophyta",
        "taxonomy_class": "Liliopsida",
        "taxonomy_order": "Poales",
        "taxonomy_family": "Poaceae",
        "taxonomy_genus": "Themeda",
        "taxonomy_species": "Themeda triandra",
    },
    {
        "province_code": "FS",
        "province_name": "Free State",
        "protection_category": "LIMITED",
        "protection_category_label": "Limited protection",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Mammalia",
        "taxonomy_order": "Cetartiodactyla",
        "taxonomy_family": "Bovidae",
        "taxonomy_genus": "Damaliscus",
        "taxonomy_species": "Damaliscus pygargus",
    },
    {
        "province_code": "LP",
        "province_name": "Limpopo",
        "protection_category": "WELL_PROTECTED",
        "protection_category_label": "Well protected",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Mammalia",
        "taxonomy_order": "Proboscidea",
        "taxonomy_family": "Elephantidae",
        "taxonomy_genus": "Loxodonta",
        "taxonomy_species": "Loxodonta africana",
    },
    {
        "province_code": "MP",
        "province_name": "Mpumalanga",
        "protection_category": "WELL_PROTECTED",
        "protection_category_label": "Well protected",
        "taxonomy_kingdom": "Plantae",
        "taxonomy_phylum": "Tracheophyta",
        "taxonomy_class": "Magnoliopsida",
        "taxonomy_order": "Fabales",
        "taxonomy_family": "Fabaceae",
        "taxonomy_genus": "Vachellia",
        "taxonomy_species": "Vachellia tortilis",
    },
    {
        "province_code": "NW",
        "province_name": "North West",
        "protection_category": "POORLY_PROTECTED",
        "protection_category_label": "Poorly protected",
        "taxonomy_kingdom": "Animalia",
        "taxonomy_phylum": "Chordata",
        "taxonomy_class": "Reptilia",
        "taxonomy_order": "Squamata",
        "taxonomy_family": "Varanidae",
        "taxonomy_genus": "Varanus",
        "taxonomy_species": "Varanus albigularis",
    },
    {
        "province_code": "NC",
        "province_name": "Northern Cape",
        "protection_category": "LIMITED",
        "protection_category_label": "Limited protection",
        "taxonomy_kingdom": "Plantae",
        "taxonomy_phylum": "Tracheophyta",
        "taxonomy_class": "Magnoliopsida",
        "taxonomy_order": "Caryophyllales",
        "taxonomy_family": "Aizoaceae",
        "taxonomy_genus": "Lithops",
        "taxonomy_species": "Lithops aucampiae",
    },
]


class Command(BaseCommand):
    help = "Seed a guaranteed approved analytics demo slice for Superset and BI verification."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_indicator_workflow_v1")
        call_command("seed_demo_spatial")

        province_type = SpatialUnitType.objects.filter(code="PROVINCE").order_by("id").first()
        province_units = _province_unit_map()
        province_layer = SpatialLayer.objects.filter(layer_code__in=PROVINCE_LAYER_CODES).order_by("id").first()

        total_points = 0
        for index, code in enumerate(DEMO_INDICATOR_CODES, start=1):
            indicator = Indicator.objects.get(code=code)
            _mark_indicator_ready(indicator)
            _ensure_target_rollup_link(indicator)
            series = IndicatorDataSeries.objects.get(indicator=indicator)
            dataset = Dataset.objects.filter(indicator_links__indicator=indicator).order_by("id").first()
            if dataset is None:
                raise CommandError(f"Indicator {code} is missing its dataset link.")
            release, _ = DatasetRelease.objects.update_or_create(
                dataset=dataset,
                version=DEMO_RELEASE_VERSION,
                defaults={
                    "release_date": DEMO_RELEASE_DATE,
                    "snapshot_title": f"{dataset.title} ({DEMO_RELEASE_VERSION})",
                    "snapshot_description": dataset.description,
                    "snapshot_methodology": dataset.methodology,
                    "provenance_json": {"source": "seed_demo_indicator_outputs", "slice": "approved_demo"},
                    "asset_manifest_json": [],
                    "organisation": dataset.organisation,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "export_approved": True,
                    "source_system": "nbms_seed",
                    "source_ref": "demo_indicator_outputs",
                },
            )
            series.status = LifecycleStatus.PUBLISHED
            series.sensitivity = SensitivityLevel.PUBLIC
            series.export_approved = True
            series.spatial_unit_type = province_type
            if province_layer:
                series.spatial_layer = province_layer
            rows = _rows_for_indicator(code, offset=index)
            series.disaggregation_schema = _build_schema(rows)
            series.save(
                update_fields=[
                    "status",
                    "sensitivity",
                    "export_approved",
                    "spatial_unit_type",
                    "spatial_layer",
                    "disaggregation_schema",
                    "updated_at",
                ]
            )

            IndicatorDataPoint.objects.filter(series=series).delete()
            IndicatorDataPoint.objects.bulk_create(
                [
                    IndicatorDataPoint(
                        series=series,
                        year=row["year"],
                        value_numeric=row["value_numeric"],
                        value_text=row.get("value_text"),
                        disaggregation=row["disaggregation"],
                        spatial_unit=province_units.get(row["disaggregation"].get("province_code", "")),
                        spatial_layer=province_layer if row["disaggregation"].get("province_code") and province_layer else None,
                        dataset_release=release,
                        source_url="https://www.sanbi.org",
                        footnote=DEMO_POINT_FOOTNOTE,
                    )
                    for row in rows
                ]
            )
            total_points += len(rows)

        Evidence.objects.filter(
            indicator_links__indicator__code__in=DEMO_INDICATOR_CODES,
            status=LifecycleStatus.PUBLISHED,
            sensitivity=SensitivityLevel.PUBLIC,
        ).update(export_approved=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded approved analytics demo outputs for {len(DEMO_INDICATOR_CODES)} indicators with {total_points} datapoints."
            )
        )


def _mark_indicator_ready(indicator: Indicator) -> None:
    indicator.status = LifecycleStatus.PUBLISHED
    indicator.sensitivity = SensitivityLevel.PUBLIC
    indicator.export_approved = True
    indicator.last_updated_on = DEMO_RELEASE_DATE
    indicator.save(update_fields=["status", "sensitivity", "export_approved", "last_updated_on", "updated_at"])


def _ensure_target_rollup_link(indicator: Indicator) -> None:
    framework_link = indicator.framework_indicator_links.select_related("framework_indicator__framework_target").order_by("id").first()
    if framework_link is None or framework_link.framework_indicator is None or framework_link.framework_indicator.framework_target is None:
        return
    NationalTargetFrameworkTargetLink.objects.update_or_create(
        national_target=indicator.national_target,
        framework_target=framework_link.framework_indicator.framework_target,
        defaults={
            "confidence": 90,
            "notes": "Seeded approved analytics rollup link.",
            "source": "seed_demo_indicator_outputs",
            "is_active": True,
        },
    )


def _province_unit_map() -> dict[str, SpatialUnit]:
    rows = (
        SpatialUnit.objects.filter(unit_type__code="PROVINCE", is_active=True)
        .order_by("unit_code", "id")
    )
    mapping: dict[str, SpatialUnit] = {}
    for row in rows:
        province_code = str((row.properties or {}).get("province_code") or "").strip()
        if province_code and province_code not in mapping:
            mapping[province_code] = row
    return mapping


def _build_schema(rows: list[dict]) -> dict:
    schema: dict[str, dict[str, str]] = {}
    for row in rows:
        for key, value in (row.get("disaggregation") or {}).items():
            schema.setdefault(key, {"type": _schema_type(value)})
    return schema


def _schema_type(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, (float, Decimal)):
        return "number"
    return "string"


def _rows_for_indicator(code: str, *, offset: int) -> list[dict]:
    handlers = {
        "NBMS-GBF-ECOSYSTEM-EXTENT": _ecosystem_extent_rows,
        "NBMS-GBF-ECOSYSTEM-THREAT": _ecosystem_threat_rows,
        "NBMS-GBF-ECOSYSTEM-PROTECTION": _ecosystem_protection_rows,
        "NBMS-GBF-SPECIES-THREAT": _species_threat_rows,
        "NBMS-GBF-SPECIES-PROTECTION": _species_protection_rows,
        "NBMS-GBF-PA-COVERAGE": _protected_area_rows,
        "NBMS-GBF-IAS-PRESSURE": _ias_pressure_rows,
        "NBMS-GBF-RESTORATION-PROGRESS": _restoration_rows,
        "NBMS-GBF-SPECIES-HABITAT-INDEX": _species_habitat_rows,
        "NBMS-GBF-GENETIC-DIVERSITY": _genetic_diversity_rows,
    }
    return handlers[code](offset)


def _timeseries_rows(*, start: Decimal, step: Decimal, label: str, extra: dict | None = None) -> list[dict]:
    rows = []
    for year_offset, year in enumerate(range(2018, 2025)):
        rows.append(
            {
                "year": year,
                "value_numeric": start + (step * Decimal(year_offset)),
                "disaggregation": {"scope": "national", "category_label": label, **(extra or {})},
            }
        )
    return rows


def _ecosystem_extent_rows(offset: int) -> list[dict]:
    rows = _timeseries_rows(start=Decimal("100.0") - Decimal(offset), step=Decimal("-0.55"), label="National extent")
    for index, province in enumerate(PROVINCES, start=1):
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("94.0") - Decimal(index) / Decimal("2.5"),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "biome_code": province["biome_code"],
                    "biome_name": province["biome"],
                    "ecosystem_type": f"{province['biome']} composite",
                    "ecosystem_type_label": f"{province['biome']} composite",
                },
            }
        )
    return rows


def _ecosystem_threat_rows(offset: int) -> list[dict]:
    categories = [
        ("CR", "Critically endangered", "UNPROTECTED", "Unprotected"),
        ("EN", "Endangered", "LIMITED", "Limited protection"),
        ("VU", "Vulnerable", "MODERATE", "Moderately protected"),
        ("NT", "Near threatened", "WELL_PROTECTED", "Well protected"),
    ]
    rows = _timeseries_rows(start=Decimal("30.0") + Decimal(offset), step=Decimal("0.60"), label="Threatened ecosystems")
    for index, province in enumerate(PROVINCES):
        threat_code, threat_label, protection_code, protection_label = categories[index % len(categories)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("6.0") + Decimal(index),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "biome_code": province["biome_code"],
                    "biome_name": province["biome"],
                    "ecosystem_type": f"{province['biome']} threatened unit",
                    "ecosystem_type_label": f"{province['biome']} threatened unit",
                    "threat_category": threat_code,
                    "threat_category_label": threat_label,
                    "protection_category": protection_code,
                    "protection_category_label": protection_label,
                    "category": threat_code,
                    "category_label": threat_label,
                },
            }
        )
    return rows


def _ecosystem_protection_rows(offset: int) -> list[dict]:
    categories = [
        ("WELL_PROTECTED", "Well protected", "NT", "Near threatened"),
        ("MODERATE", "Moderately protected", "VU", "Vulnerable"),
        ("LIMITED", "Limited protection", "EN", "Endangered"),
        ("UNPROTECTED", "Unprotected", "CR", "Critically endangered"),
    ]
    rows = _timeseries_rows(start=Decimal("40.0") + Decimal(offset), step=Decimal("0.75"), label="Protected ecosystems")
    for index, province in enumerate(PROVINCES):
        protection_code, protection_label, threat_code, threat_label = categories[index % len(categories)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("9.0") + Decimal(index),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "biome_code": province["biome_code"],
                    "biome_name": province["biome"],
                    "ecosystem_type": f"{province['biome']} protection unit",
                    "ecosystem_type_label": f"{province['biome']} protection unit",
                    "protection_category": protection_code,
                    "protection_category_label": protection_label,
                    "threat_category": threat_code,
                    "threat_category_label": threat_label,
                    "category": protection_code,
                    "category_label": protection_label,
                },
            }
        )
    return rows


def _species_threat_rows(offset: int) -> list[dict]:
    rows = _timeseries_rows(start=Decimal("96.0") + Decimal(offset), step=Decimal("3.0"), label="Threatened species")
    for index, taxon in enumerate(TAXONOMY_THREAT_ROWS, start=1):
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("4") + Decimal(index),
                "disaggregation": taxon,
            }
        )
    return rows


def _species_protection_rows(offset: int) -> list[dict]:
    rows = _timeseries_rows(start=Decimal("42.0") + Decimal(offset), step=Decimal("1.75"), label="Protected species")
    for index, taxon in enumerate(TAXONOMY_PROTECTION_ROWS, start=1):
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("12") + Decimal(index),
                "disaggregation": taxon,
            }
        )
    return rows


def _protected_area_rows(offset: int) -> list[dict]:
    progress_cycle = [("ON_TRACK", "On track"), ("ACCELERATE", "Needs acceleration"), ("OFF_TRACK", "Off track")]
    rows = _timeseries_rows(start=Decimal("14.5") + (Decimal(offset) / Decimal("10")), step=Decimal("0.55"), label="Protected area coverage")
    for index, province in enumerate(PROVINCES):
        progress_code, progress_label = progress_cycle[index % len(progress_cycle)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("13.5") + Decimal(index) / Decimal("1.7"),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "protected_area_type": "Formal protected area" if index % 2 == 0 else "OECM",
                    "target_progress": progress_code,
                    "target_progress_label": progress_label,
                },
            }
        )
    return rows


def _ias_pressure_rows(offset: int) -> list[dict]:
    pathways = [
        ("ESCAPE", "High"),
        ("STOWAWAY", "Medium"),
        ("RELEASE", "High"),
        ("CORRIDOR", "Low"),
    ]
    rows = _timeseries_rows(start=Decimal("60.0") - Decimal(offset), step=Decimal("-1.15"), label="IAS pressure")
    for index, province in enumerate(PROVINCES):
        pathway, pressure = pathways[index % len(pathways)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("45.0") + Decimal(index) / Decimal("1.3"),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "pathway": pathway,
                    "pressure_category": pressure.upper(),
                    "pressure_category_label": pressure,
                },
            }
        )
    return rows


def _restoration_rows(offset: int) -> list[dict]:
    statuses = [
        ("RESTORED", "Restored", "ON_TRACK", "On track"),
        ("RECOVERING", "Recovering", "ACCELERATE", "Needs acceleration"),
        ("DEGRADED", "Degraded", "OFF_TRACK", "Off track"),
    ]
    rows = _timeseries_rows(start=Decimal("11.0") + Decimal(offset), step=Decimal("1.35"), label="Restoration progress")
    for index, province in enumerate(PROVINCES):
        status_code, status_label, progress_code, progress_label = statuses[index % len(statuses)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("8.0") + Decimal(index) / Decimal("1.2"),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "biome_code": province["biome_code"],
                    "biome_name": province["biome"],
                    "restoration_status": status_code,
                    "restoration_status_label": status_label,
                    "target_progress": progress_code,
                    "target_progress_label": progress_label,
                },
            }
        )
    return rows


def _species_habitat_rows(offset: int) -> list[dict]:
    bands = [("HIGH", "High integrity"), ("MODERATE", "Moderate integrity"), ("LOW", "Low integrity")]
    families = ["Felidae", "Proteaceae", "Gruidae", "Accipitridae", "Cercopithecidae"]
    rows = _timeseries_rows(start=Decimal("74.0") - Decimal(offset) / Decimal("2"), step=Decimal("-0.80"), label="Species habitat index")
    for index, province in enumerate(PROVINCES):
        band_code, band_label = bands[index % len(bands)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal("55.0") + Decimal(index),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "taxonomy_family": families[index % len(families)],
                    "habitat_index_band": band_code,
                    "habitat_index_band_label": band_label,
                },
            }
        )
    return rows


def _genetic_diversity_rows(offset: int) -> list[dict]:
    bands = [("STABLE", "Stable"), ("WATCH", "Watchlist"), ("ERODING", "Eroding")]
    statuses = [("approved", "Approved"), ("review", "Review"), ("gap", "Gap")]
    rows = _timeseries_rows(start=Decimal("60.0") + Decimal(offset) / Decimal("2"), step=Decimal("0.50"), label="Genetic diversity status")
    for index, province in enumerate(PROVINCES):
        band_code, band_label = bands[index % len(bands)]
        status_code, status_label = statuses[index % len(statuses)]
        rows.append(
            {
                "year": 2024,
                "value_numeric": Decimal(index % 2),
                "disaggregation": {
                    "province_code": province["code"],
                    "province_name": province["name"],
                    "genetic_diversity_band": band_code,
                    "genetic_diversity_band_label": band_label,
                    "policy_status": status_code,
                    "policy_status_label": status_label,
                    "category": band_code.lower(),
                    "category_label": band_label,
                },
            }
        )
    return rows
