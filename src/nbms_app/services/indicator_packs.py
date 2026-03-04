from __future__ import annotations

from copy import deepcopy

from nbms_app.models import Indicator


_TAXONOMY_LEVELS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]


def _dimension(
    id: str,
    label: str,
    type: str,
    join_key: str,
    sort_order: int,
    *,
    allowed_levels: list[str] | None = None,
    legend_id: str | None = None,
    description: str = "",
    default_group_by: str | None = None,
    allowed_group_bys: list[str] | None = None,
) -> dict:
    return {
        "id": id,
        "label": label,
        "type": type,
        "allowed_levels": allowed_levels or [],
        "join_key": join_key,
        "sort_order": sort_order,
        "legend_id": legend_id,
        "description": description,
        "default_group_by": default_group_by,
        "allowed_group_bys": allowed_group_bys or [],
    }


_DIMENSIONS = {
    "year": _dimension("year", "Year", "time", "year", 10, allowed_levels=["year"], default_group_by="year"),
    "release": _dimension("release", "Dataset release", "categorical", "dataset_release_uuid", 15),
    "province": _dimension(
        "province",
        "Province",
        "geo",
        "province_code",
        20,
        allowed_levels=["province"],
        default_group_by="province",
    ),
    "municipality": _dimension(
        "municipality",
        "Municipality",
        "geo",
        "municipality_code",
        22,
        allowed_levels=["municipality"],
    ),
    "biome": _dimension("biome", "Biome", "geo", "biome_code", 24, allowed_levels=["biome"]),
    "ecoregion": _dimension("ecoregion", "Ecoregion", "geo", "ecoregion_code", 26, allowed_levels=["ecoregion"]),
    "realm": _dimension("realm", "Realm", "geo", "realm_code", 28, allowed_levels=["realm"]),
    "threat_category": _dimension(
        "threat_category",
        "Threat category",
        "categorical",
        "threat_category",
        30,
        legend_id="threat_category",
    ),
    "rle_category": _dimension(
        "rle_category",
        "RLE category",
        "categorical",
        "rle_category",
        31,
        legend_id="rle_category",
    ),
    "protection_category": _dimension(
        "protection_category",
        "Protection category",
        "categorical",
        "protection_category",
        32,
        legend_id="protection_category",
    ),
    "epl_category": _dimension(
        "epl_category",
        "EPL category",
        "categorical",
        "epl_category",
        33,
        legend_id="epl_category",
    ),
    "spi_category": _dimension(
        "spi_category",
        "SPI category",
        "categorical",
        "spi_category",
        34,
        legend_id="spi_category",
    ),
    "category": _dimension("category", "Category", "categorical", "category", 35),
    "pathway": _dimension("pathway", "Pathway", "categorical", "pathway", 36, legend_id="ias_pathway"),
    "pressure_category": _dimension(
        "pressure_category",
        "Pressure category",
        "categorical",
        "pressure_category",
        38,
        legend_id="pressure_category",
    ),
    "target_progress": _dimension(
        "target_progress",
        "Target progress",
        "categorical",
        "target_progress",
        40,
        legend_id="target_progress",
    ),
    "ecosystem_type": _dimension("ecosystem_type", "Ecosystem type", "categorical", "ecosystem_type", 42),
    "protected_area_type": _dimension(
        "protected_area_type",
        "Protected area type",
        "categorical",
        "protected_area_type",
        44,
    ),
    "restoration_status": _dimension(
        "restoration_status",
        "Restoration status",
        "categorical",
        "restoration_status",
        46,
        legend_id="restoration_status",
    ),
    "habitat_index_band": _dimension(
        "habitat_index_band",
        "Habitat index band",
        "categorical",
        "habitat_index_band",
        48,
        legend_id="habitat_index_band",
    ),
    "genetic_diversity_band": _dimension(
        "genetic_diversity_band",
        "Genetic diversity band",
        "categorical",
        "genetic_diversity_band",
        50,
        legend_id="genetic_diversity_band",
    ),
    "policy_status": _dimension("policy_status", "Policy status", "categorical", "policy_status", 52),
    "pollution_type": _dimension(
        "pollution_type",
        "Pollution type",
        "categorical",
        "pollution_type",
        54,
        legend_id="pollution_type",
    ),
    "climate_pressure": _dimension(
        "climate_pressure",
        "Climate pressure",
        "categorical",
        "climate_pressure",
        56,
        legend_id="climate_pressure",
    ),
    "taxonomy": _dimension(
        "taxonomy",
        "Taxonomy",
        "hierarchy",
        "taxonomy",
        58,
        allowed_levels=_TAXONOMY_LEVELS,
        default_group_by="taxonomy_family",
    ),
}

for index, level in enumerate(_TAXONOMY_LEVELS, start=60):
    _DIMENSIONS[f"taxonomy_{level}"] = _dimension(
        f"taxonomy_{level}",
        level.title(),
        "hierarchy",
        f"taxonomy_{level}",
        index,
        allowed_levels=_TAXONOMY_LEVELS,
        default_group_by=f"taxonomy_{level}",
    )


_LEGENDS = {
    "threat_category": {
        "id": "threat_category",
        "title": "Threat category legend",
        "dimensionId": "threat_category",
        "items": [
            {"value": "CR", "label": "Critically endangered", "colorToken": "--nbms-danger"},
            {"value": "EN", "label": "Endangered", "colorToken": "--nbms-warn"},
            {"value": "VU", "label": "Vulnerable", "colorToken": "--nbms-accent-500"},
            {"value": "NT", "label": "Near threatened", "colorToken": "--nbms-info"},
            {"value": "LC", "label": "Least concern", "colorToken": "--nbms-success"},
        ],
    },
    "rle_category": {
        "id": "rle_category",
        "title": "RLE category legend",
        "dimensionId": "rle_category",
        "items": [
            {"value": "CR", "label": "Critically endangered", "colorToken": "--nbms-danger"},
            {"value": "EN", "label": "Endangered", "colorToken": "--nbms-warn"},
            {"value": "VU", "label": "Vulnerable", "colorToken": "--nbms-accent-500"},
            {"value": "NT", "label": "Near threatened", "colorToken": "--nbms-info"},
            {"value": "LC", "label": "Least concern", "colorToken": "--nbms-success"},
        ],
    },
    "protection_category": {
        "id": "protection_category",
        "title": "Protection category legend",
        "dimensionId": "protection_category",
        "items": [
            {"value": "WELL_PROTECTED", "label": "Well protected", "colorToken": "--nbms-success"},
            {"value": "MODERATE", "label": "Moderately protected", "colorToken": "--nbms-info"},
            {"value": "LIMITED", "label": "Limited protection", "colorToken": "--nbms-warn"},
            {"value": "UNPROTECTED", "label": "Unprotected", "colorToken": "--nbms-danger"},
        ],
    },
    "epl_category": {
        "id": "epl_category",
        "title": "EPL category legend",
        "dimensionId": "epl_category",
        "items": [
            {"value": "WP", "label": "Well protected", "colorToken": "--nbms-success"},
            {"value": "MP", "label": "Moderately protected", "colorToken": "--nbms-info"},
            {"value": "PP", "label": "Poorly protected", "colorToken": "--nbms-warn"},
            {"value": "NP", "label": "Not protected", "colorToken": "--nbms-danger"},
        ],
    },
    "spi_category": {
        "id": "spi_category",
        "title": "Plant SPI category legend",
        "dimensionId": "spi_category",
        "items": [
            {"value": "WP", "label": "Well protected", "colorToken": "--nbms-success"},
            {"value": "MP", "label": "Moderately protected", "colorToken": "--nbms-info"},
            {"value": "PP", "label": "Poorly protected", "colorToken": "--nbms-warn"},
            {"value": "NP", "label": "Not protected", "colorToken": "--nbms-danger"},
        ],
    },
    "ias_pathway": {
        "id": "ias_pathway",
        "title": "IAS pathway legend",
        "dimensionId": "pathway",
        "items": [
            {"value": "ESCAPE", "label": "Escape", "colorToken": "--nbms-info"},
            {"value": "STOWAWAY", "label": "Stowaway", "colorToken": "--nbms-accent-500"},
            {"value": "RELEASE", "label": "Release", "colorToken": "--nbms-warn"},
            {"value": "CORRIDOR", "label": "Corridor", "colorToken": "--nbms-danger"},
        ],
    },
    "pressure_category": {
        "id": "pressure_category",
        "title": "Pressure legend",
        "dimensionId": "pressure_category",
        "items": [
            {"value": "HIGH", "label": "High pressure", "colorToken": "--nbms-danger"},
            {"value": "MEDIUM", "label": "Medium pressure", "colorToken": "--nbms-warn"},
            {"value": "LOW", "label": "Low pressure", "colorToken": "--nbms-success"},
        ],
    },
    "target_progress": {
        "id": "target_progress",
        "title": "Target progress legend",
        "dimensionId": "target_progress",
        "items": [
            {"value": "ON_TRACK", "label": "On track", "colorToken": "--nbms-success"},
            {"value": "ACCELERATE", "label": "Needs acceleration", "colorToken": "--nbms-warn"},
            {"value": "OFF_TRACK", "label": "Off track", "colorToken": "--nbms-danger"},
        ],
    },
    "restoration_status": {
        "id": "restoration_status",
        "title": "Restoration status legend",
        "dimensionId": "restoration_status",
        "items": [
            {"value": "RESTORED", "label": "Restored", "colorToken": "--nbms-success"},
            {"value": "RECOVERING", "label": "Recovering", "colorToken": "--nbms-info"},
            {"value": "DEGRADED", "label": "Degraded", "colorToken": "--nbms-danger"},
        ],
    },
    "habitat_index_band": {
        "id": "habitat_index_band",
        "title": "Habitat integrity legend",
        "dimensionId": "habitat_index_band",
        "items": [
            {"value": "HIGH", "label": "High integrity", "colorToken": "--nbms-success"},
            {"value": "MODERATE", "label": "Moderate integrity", "colorToken": "--nbms-info"},
            {"value": "LOW", "label": "Low integrity", "colorToken": "--nbms-danger"},
        ],
    },
    "genetic_diversity_band": {
        "id": "genetic_diversity_band",
        "title": "Genetic diversity legend",
        "dimensionId": "genetic_diversity_band",
        "items": [
            {"value": "STABLE", "label": "Stable", "colorToken": "--nbms-success"},
            {"value": "WATCH", "label": "Watchlist", "colorToken": "--nbms-warn"},
            {"value": "ERODING", "label": "Eroding", "colorToken": "--nbms-danger"},
        ],
    },
    "pollution_type": {
        "id": "pollution_type",
        "title": "Pollution legend",
        "dimensionId": "pollution_type",
        "items": [
            {"value": "NUTRIENT", "label": "Nutrient loading", "colorToken": "--nbms-info"},
            {"value": "PLASTIC", "label": "Plastic and waste", "colorToken": "--nbms-warn"},
            {"value": "CHEMICAL", "label": "Chemical stress", "colorToken": "--nbms-danger"},
        ],
    },
    "climate_pressure": {
        "id": "climate_pressure",
        "title": "Climate pressure legend",
        "dimensionId": "climate_pressure",
        "items": [
            {"value": "HIGH", "label": "High exposure", "colorToken": "--nbms-danger"},
            {"value": "MEDIUM", "label": "Moderate exposure", "colorToken": "--nbms-warn"},
            {"value": "LOW", "label": "Low exposure", "colorToken": "--nbms-success"},
        ],
    },
}


def _narrative_templates(subject: str, hook: str) -> list[dict]:
    return [
        {
            "id": "interpretation",
            "title": "Interpretation",
            "body": f"Summarize the current signal for {subject}. Focus on the current slice and note whether the pattern is improving, stable, or deteriorating.",
        },
        {
            "id": "key-messages",
            "title": "Key messages",
            "body": f"Record two or three short messages that decision-makers should retain from the {subject} pack. Include the strongest pattern in {hook}.",
        },
        {
            "id": "data-limitations",
            "title": "Data limitations",
            "body": f"Document any release, QA, or spatial limitations that affect the interpretation of {subject}.",
        },
        {
            "id": "what-changed",
            "title": "What changed",
            "body": f"Explain what changed since the previous release for {subject}, including methodology, geography, or categorical reclassification.",
        },
    ]


def _matrix_definition(id: str, label: str, x_dimension: str, y_dimension: str) -> dict:
    return {
        "id": id,
        "label": label,
        "xDimension": x_dimension,
        "yDimension": y_dimension,
    }


_PACKS = [
    {
        "id": "ecosystem_rle",
        "label": "Ecosystem RLE",
        "aliases": ["NBA_ECO_RLE_TERR", "NBA_ECO_RLE_EST", "rle terr", "rle est"],
        "default_view": "distribution",
        "available_views": ["distribution", "matrix", "timeseries"],
        "default_group_by": "rle_category",
        "default_agg": "biome",
        "dimensions": ["year", "biome", "ecoregion", "realm", "ecosystem_type", "rle_category", "epl_category", "get_code"],
        "map_layers": [
            {
                "layerCodes": ["ZA_BIOMES", "ZA_ECOSYSTEM_THREAT_STATUS", "ZA_PROVINCES"],
                "title": "Ecosystem RLE",
                "joinKey": "biome_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["rle_category", "epl_category"],
        "matrix_definitions": [_matrix_definition("rle_x_epl", "RLE x EPL", "rle_category", "epl_category")],
        "narrative_templates": _narrative_templates("ecosystem threat status", "the threatened and under-protected ecosystem mix"),
    },
    {
        "id": "ecosystem_epl",
        "label": "Ecosystem EPL",
        "aliases": ["NBA_ECO_EPL_TERR", "epl terr"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries", "matrix"],
        "default_group_by": "epl_category",
        "default_agg": "biome",
        "dimensions": ["year", "biome", "realm", "ecosystem_type", "epl_category", "target_progress"],
        "map_layers": [
            {
                "layerCodes": ["ZA_BIOMES", "ZA_PROVINCES"],
                "title": "Ecosystem EPL",
                "joinKey": "biome_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["epl_category", "target_progress"],
        "matrix_definitions": [_matrix_definition("epl_x_target_progress", "EPL x target progress", "epl_category", "target_progress")],
        "narrative_templates": _narrative_templates("ecosystem protection level", "where protection outcomes are strongest and weakest"),
    },
    {
        "id": "ecosystem_rle_x_epl_matrix",
        "label": "Ecosystem RLE x EPL Matrix",
        "aliases": ["NBA_ECO_RLE_EPL_TERR_MATRIX", "NBA_ECO_RLE_EPL_EST_MATRIX", "rle epl matrix"],
        "default_view": "matrix",
        "available_views": ["matrix", "distribution"],
        "default_group_by": "rle_category",
        "default_agg": "biome",
        "dimensions": ["year", "biome", "ecoregion", "realm", "ecosystem_type", "rle_category", "epl_category"],
        "map_layers": [
            {
                "layerCodes": ["ZA_BIOMES", "ZA_PROVINCES"],
                "title": "Threat x protection hotspots",
                "joinKey": "biome_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["rle_category", "epl_category"],
        "matrix_definitions": [_matrix_definition("rle_x_epl", "RLE x EPL", "rle_category", "epl_category")],
        "narrative_templates": _narrative_templates("threat and protection intersections", "where high threat and low protection overlap"),
    },
    {
        "id": "tepi_timeseries",
        "label": "TEPI Timeseries",
        "aliases": ["NBA_TEPI_TERR", "NBA_ECO_EPLI_TERR", "tepi", "epli"],
        "default_view": "timeseries",
        "available_views": ["timeseries", "distribution"],
        "default_group_by": "biome",
        "default_agg": "biome",
        "dimensions": ["year", "biome", "target_progress"],
        "map_layers": [
            {
                "layerCodes": ["ZA_BIOMES", "ZA_PROVINCES"],
                "title": "Biome protection progress",
                "joinKey": "biome_code",
                "availableMetrics": ["value", "change", "coverage", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["target_progress"],
        "narrative_templates": _narrative_templates("ecosystem protection progress", "which biomes are improving protection coverage over time"),
    },
    {
        "id": "plant_spi_taxonomy",
        "label": "Plant SPI Taxonomy",
        "aliases": ["NBA_PLANT_SPI", "plant spi", "plant protection"],
        "default_view": "taxonomy",
        "available_views": ["taxonomy", "distribution", "timeseries"],
        "default_group_by": "taxonomy_family",
        "default_agg": "province",
        "dimensions": [
            "year",
            "province",
            "biome",
            "spi_category",
            "taxonomy",
            "taxonomy_kingdom",
            "taxonomy_phylum",
            "taxonomy_class",
            "taxonomy_order",
            "taxonomy_family",
            "taxonomy_genus",
            "taxonomy_species",
        ],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES_NE", "ZA_PROVINCES"],
                "title": "Plant SPI by province",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["spi_category"],
        "narrative_templates": _narrative_templates("plant species protection level", "which lineages and provinces remain most exposed"),
    },
    {
        "id": "binary_admin_status",
        "label": "Binary Admin Status",
        "aliases": ["binary admin", "reporting completeness"],
        "default_view": "binary",
        "available_views": ["binary", "distribution"],
        "default_group_by": "policy_status",
        "default_agg": "year",
        "dimensions": ["year", "policy_status", "category"],
        "map_layers": [],
        "legends": [],
        "narrative_templates": _narrative_templates("binary governance status", "whether the required administrative conditions are in place"),
    },
    {
        "id": "ecosystem_threat_status",
        "label": "Ecosystem threat status",
        "aliases": ["NBMS-GBF-ECOSYSTEM-THREAT", "RLE", "ecosystem threat"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries", "matrix"],
        "default_group_by": "threat_category",
        "default_agg": "province",
        "dimensions": ["year", "province", "biome", "threat_category", "protection_category", "ecosystem_type"],
        "map_layers": [
            {
                "layerCodes": ["ZA_ECOSYSTEM_THREAT_STATUS", "ZA_PROVINCES"],
                "title": "Ecosystem threat status",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["threat_category", "protection_category"],
        "matrix_definitions": [_matrix_definition("threat_x_protection", "Threat x protection", "threat_category", "protection_category")],
        "narrative_templates": _narrative_templates("ecosystem threat status", "the threat and protection mix"),
    },
    {
        "id": "ecosystem_protection_level",
        "label": "Ecosystem protection level",
        "aliases": ["NBMS-GBF-ECOSYSTEM-PROTECTION", "ecosystem protection"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries", "matrix"],
        "default_group_by": "protection_category",
        "default_agg": "province",
        "dimensions": ["year", "province", "biome", "protection_category", "threat_category", "ecosystem_type"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES", "ZA_ECOSYSTEM_THREAT_STATUS"],
                "title": "Ecosystem protection",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["protection_category", "threat_category"],
        "matrix_definitions": [_matrix_definition("protection_x_threat", "Protection x threat", "protection_category", "threat_category")],
        "narrative_templates": _narrative_templates("ecosystem protection level", "the protected versus threatened ecosystem mix"),
    },
    {
        "id": "species_threat_status",
        "label": "Species threat status",
        "aliases": ["NBMS-GBF-SPECIES-THREAT", "IND-RICH", "species threat", "threatened species"],
        "default_view": "taxonomy",
        "available_views": ["taxonomy", "distribution", "timeseries"],
        "default_group_by": "taxonomy_family",
        "default_agg": "province",
        "dimensions": [
            "year",
            "province",
            "threat_category",
            "taxonomy",
            "taxonomy_kingdom",
            "taxonomy_phylum",
            "taxonomy_class",
            "taxonomy_order",
            "taxonomy_family",
            "taxonomy_genus",
            "taxonomy_species",
        ],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES_NE", "ZA_PROVINCES"],
                "title": "Species threat by province",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["threat_category"],
        "narrative_templates": _narrative_templates("species threat status", "which taxa and provinces are driving the threatened slice"),
    },
    {
        "id": "species_protection_level",
        "label": "Species protection level",
        "aliases": ["NBMS-GBF-SPECIES-PROTECTION", "species protection"],
        "default_view": "taxonomy",
        "available_views": ["taxonomy", "distribution", "timeseries"],
        "default_group_by": "taxonomy_family",
        "default_agg": "province",
        "dimensions": [
            "year",
            "province",
            "protection_category",
            "taxonomy",
            "taxonomy_kingdom",
            "taxonomy_phylum",
            "taxonomy_class",
            "taxonomy_order",
            "taxonomy_family",
            "taxonomy_genus",
            "taxonomy_species",
        ],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES_NE", "ZA_PROVINCES"],
                "title": "Species protection by province",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["protection_category"],
        "narrative_templates": _narrative_templates("species protection level", "which taxonomic groups remain under-protected"),
    },
    {
        "id": "protected_area_coverage",
        "label": "Protected area coverage",
        "aliases": ["NBMS-GBF-PA-COVERAGE", "protected area coverage"],
        "default_view": "timeseries",
        "available_views": ["timeseries", "distribution"],
        "default_group_by": "province",
        "default_agg": "province",
        "dimensions": ["year", "province", "protected_area_type", "target_progress"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROTECTED_AREAS", "ZA_PROTECTED_AREAS_NE", "ZA_PROVINCES"],
                "title": "Protected area coverage",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["target_progress"],
        "narrative_templates": _narrative_templates("protected area coverage", "the pace of change against the 30 by 30 target"),
    },
    {
        "id": "ias_pressure",
        "label": "Invasive alien species pressure",
        "aliases": ["NBMS-GBF-IAS-PRESSURE", "ias pressure", "invasive alien"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries"],
        "default_group_by": "pathway",
        "default_agg": "province",
        "dimensions": ["year", "province", "pathway", "pressure_category"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "IAS pressure",
                "joinKey": "province_code",
                "availableMetrics": ["value", "coverage", "change", "uncertainty"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["ias_pathway", "pressure_category"],
        "narrative_templates": _narrative_templates("IAS pressure", "pathways and provinces carrying the highest invasion pressure"),
    },
    {
        "id": "ecosystem_extent",
        "label": "Ecosystem extent",
        "aliases": ["NBMS-GBF-ECOSYSTEM-EXTENT", "ecosystem extent"],
        "default_view": "timeseries",
        "available_views": ["timeseries", "distribution"],
        "default_group_by": "biome",
        "default_agg": "biome",
        "dimensions": ["year", "biome", "province", "ecosystem_type"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "Ecosystem extent",
                "joinKey": "province_code",
                "availableMetrics": ["value", "change", "coverage"],
                "defaultMetric": "value",
            }
        ],
        "legends": [],
        "narrative_templates": _narrative_templates("ecosystem extent", "where extent losses or gains are concentrated"),
    },
    {
        "id": "restoration_progress",
        "label": "Restoration progress",
        "aliases": ["NBMS-GBF-RESTORATION-PROGRESS", "restoration progress"],
        "default_view": "timeseries",
        "available_views": ["timeseries", "distribution"],
        "default_group_by": "restoration_status",
        "default_agg": "province",
        "dimensions": ["year", "province", "biome", "restoration_status", "target_progress"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "Restoration progress",
                "joinKey": "province_code",
                "availableMetrics": ["value", "change", "coverage"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["restoration_status", "target_progress"],
        "narrative_templates": _narrative_templates("restoration progress", "where recovery is accelerating and where the programme is lagging"),
    },
    {
        "id": "species_habitat_index",
        "label": "Species habitat index",
        "aliases": ["NBMS-GBF-SPECIES-HABITAT-INDEX", "habitat index"],
        "default_view": "timeseries",
        "available_views": ["timeseries", "distribution"],
        "default_group_by": "habitat_index_band",
        "default_agg": "province",
        "dimensions": ["year", "province", "habitat_index_band", "taxonomy_family"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "Species habitat index",
                "joinKey": "province_code",
                "availableMetrics": ["value", "change", "coverage"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["habitat_index_band"],
        "narrative_templates": _narrative_templates("species habitat index", "which provinces or lineages are losing habitat integrity"),
    },
    {
        "id": "genetic_diversity",
        "label": "Genetic diversity",
        "aliases": ["NBMS-GBF-GENETIC-DIVERSITY", "genetic diversity"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries", "binary"],
        "default_group_by": "genetic_diversity_band",
        "default_agg": "province",
        "dimensions": ["year", "province", "genetic_diversity_band", "policy_status"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "Genetic diversity",
                "joinKey": "province_code",
                "availableMetrics": ["value", "change", "coverage"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["genetic_diversity_band"],
        "narrative_templates": _narrative_templates("genetic diversity", "where erosion is emerging and whether current safeguards are adequate"),
    },
    {
        "id": "pollution_risk",
        "label": "Pollution risk",
        "aliases": ["NBMS-GBF-POLLUTION-RISK", "pollution risk"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries"],
        "default_group_by": "pollution_type",
        "default_agg": "province",
        "dimensions": ["year", "province", "pollution_type", "pressure_category"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "Pollution risk",
                "joinKey": "province_code",
                "availableMetrics": ["value", "change", "coverage"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["pollution_type", "pressure_category"],
        "narrative_templates": _narrative_templates("pollution risk", "the dominant pollution sources and geographies of concern"),
    },
    {
        "id": "climate_biodiversity_pressure",
        "label": "Climate-biodiversity pressure",
        "aliases": ["NBMS-GBF-CLIMATE-BIODIVERSITY-PRESSURE", "climate biodiversity"],
        "default_view": "distribution",
        "available_views": ["distribution", "timeseries"],
        "default_group_by": "climate_pressure",
        "default_agg": "province",
        "dimensions": ["year", "province", "climate_pressure", "biome"],
        "map_layers": [
            {
                "layerCodes": ["ZA_PROVINCES"],
                "title": "Climate-biodiversity pressure",
                "joinKey": "province_code",
                "availableMetrics": ["value", "change", "coverage"],
                "defaultMetric": "value",
            }
        ],
        "legends": ["climate_pressure"],
        "narrative_templates": _narrative_templates("climate-biodiversity pressure", "where biodiversity exposure to climate pressure is intensifying"),
    },
]


def copy_dimension(dimension_id: str, **overrides) -> dict:
    row = deepcopy(_DIMENSIONS[dimension_id])
    row.update({key: value for key, value in overrides.items() if value is not None})
    return row


def list_pack_definitions() -> list[dict]:
    return [deepcopy(pack) for pack in _PACKS]


def list_pack_dimensions() -> list[dict]:
    return sorted((deepcopy(row) for row in _DIMENSIONS.values()), key=lambda row: (row["sort_order"], row["label"]))


def find_pack(pack_id: str | None) -> dict | None:
    normalized = str(pack_id or "").strip().lower()
    if not normalized:
        return None
    for pack in _PACKS:
        if pack["id"] == normalized:
            return deepcopy(pack)
    return None


def resolve_indicator_pack(indicator: Indicator, *, tags: list[str] | None = None) -> dict:
    explicit_pack = find_pack(getattr(indicator, "visual_pack_id", ""))
    if explicit_pack is not None:
        return explicit_pack

    haystack = " ".join(
        filter(
            None,
            [
                str(indicator.code or "").lower(),
                str(indicator.title or "").lower(),
                str(indicator.national_target.code if indicator.national_target_id else "").lower(),
                str(indicator.national_target.title if indicator.national_target_id else "").lower(),
                " ".join(str(tag).lower() for tag in (tags or [])),
            ],
        )
    )
    scored: list[tuple[int, dict]] = []
    for pack in _PACKS:
        score = 0
        for alias in pack["aliases"]:
            normalized = str(alias).strip().lower()
            if not normalized:
                continue
            if normalized == str(indicator.code or "").lower():
                score += 10
            elif normalized in haystack:
                score += 4
        if score:
            scored.append((score, pack))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1]["label"]))
        return deepcopy(scored[0][1])

    taxonomy_hint = "species" in haystack or "taxonomy" in haystack
    if taxonomy_hint:
        return deepcopy(find_pack("species_threat_status") or _PACKS[0])
    return deepcopy(find_pack("ecosystem_extent") or _PACKS[0])


def build_pack_dimensions(pack: dict, observed_dimensions: list[dict]) -> list[dict]:
    dimension_map = {row["id"]: deepcopy(row) for row in observed_dimensions}
    for dimension_id in pack.get("dimensions", []):
        if dimension_id in _DIMENSIONS:
            base = copy_dimension(dimension_id)
            observed = dimension_map.get(dimension_id)
            if observed:
                base.update(
                    {
                        "join_key": observed.get("join_key") or base["join_key"],
                        "allowed_levels": observed.get("allowed_levels") or base["allowed_levels"],
                    }
                )
            dimension_map[dimension_id] = base
    return sorted(dimension_map.values(), key=lambda row: (row["sort_order"], row["label"]))


def build_pack_profile(pack: dict, *, dimensions: list[dict], map_layers: list[dict], meta: dict) -> dict:
    hierarchy_levels = [
        {"id": level, "label": copy_dimension(f"taxonomy_{level}")["label"]}
        for level in _TAXONOMY_LEVELS
        if any(row["id"] == f"taxonomy_{level}" for row in dimensions)
    ]
    return {
        "packId": pack["id"],
        "packLabel": pack["label"],
        "defaultView": pack["default_view"],
        "availableViews": pack["available_views"],
        "supportedDimensions": [row["id"] for row in dimensions],
        "hierarchyDefinitions": (
            [{"id": "taxonomy", "label": "Taxonomy", "levels": hierarchy_levels}] if hierarchy_levels else []
        ),
        "defaultGroupBy": pack["default_group_by"],
        "defaultAgg": pack["default_agg"],
        "mapLayers": map_layers,
        "legends": [deepcopy(_LEGENDS[item]) for item in pack.get("legends", []) if item in _LEGENDS],
        "matrixDefinitions": deepcopy(pack.get("matrix_definitions", [])),
        "narrativeTemplates": deepcopy(pack.get("narrative_templates", [])),
        "meta": meta,
    }
