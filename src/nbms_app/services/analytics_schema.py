from __future__ import annotations

from collections.abc import Iterable

from django.db import connection

from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Evidence,
    Framework,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodologyVersionLink,
    License,
    Methodology,
    MethodologyVersion,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    SpatialFeature,
    SpatialLayer,
    SpatialUnit,
    SpatialUnitType,
)
from nbms_app.spatial_fields import GIS_ENABLED


ANALYTICS_SCHEMA = "analytics"

FACT_INDICATOR_OBSERVATION_VIEW = f"{ANALYTICS_SCHEMA}.fact_indicator_observation"
FACT_READINESS_VIEW = f"{ANALYTICS_SCHEMA}.fact_readiness"
FACT_TARGET_ROLLUP_VIEW = f"{ANALYTICS_SCHEMA}.fact_target_rollup"

DIM_INDICATOR_VIEW = f"{ANALYTICS_SCHEMA}.dim_indicator"
DIM_FRAMEWORK_TARGET_VIEW = f"{ANALYTICS_SCHEMA}.dim_framework_target"
DIM_GEOGRAPHY_VIEW = f"{ANALYTICS_SCHEMA}.dim_geography"
DIM_DATASET_RELEASE_VIEW = f"{ANALYTICS_SCHEMA}.dim_dataset_release"
DIM_METHOD_VERSION_VIEW = f"{ANALYTICS_SCHEMA}.dim_method_version"

BOUNDARY_PROVINCE_GEOJSON_VIEW = f"{ANALYTICS_SCHEMA}.boundary_province_geojson"
INDICATOR_SPATIAL_GEOJSON_VIEW = f"{ANALYTICS_SCHEMA}.indicator_spatial_geojson"

INDICATOR_REGISTRY_VIEW = f"{ANALYTICS_SCHEMA}.indicator_registry"
INDICATOR_LATEST_VALUE_VIEW = f"{ANALYTICS_SCHEMA}.indicator_latest_value"
INDICATOR_TIMESERIES_VIEW = f"{ANALYTICS_SCHEMA}.indicator_timeseries"
FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW = f"{ANALYTICS_SCHEMA}.framework_target_indicator_links"
INDICATOR_READINESS_SUMMARY_VIEW = f"{ANALYTICS_SCHEMA}.indicator_readiness_summary"
SPATIAL_UNITS_GEOJSON_VIEW = f"{ANALYTICS_SCHEMA}.spatial_units_geojson"
INDICATOR_SPATIAL_FEATURES_GEOJSON_VIEW = f"{ANALYTICS_SCHEMA}.indicator_spatial_features_geojson"


def _table(model) -> str:
    return model._meta.db_table


def analytics_view_names() -> list[str]:
    return [
        FACT_INDICATOR_OBSERVATION_VIEW,
        DIM_INDICATOR_VIEW,
        DIM_FRAMEWORK_TARGET_VIEW,
        DIM_GEOGRAPHY_VIEW,
        DIM_DATASET_RELEASE_VIEW,
        DIM_METHOD_VERSION_VIEW,
        FACT_READINESS_VIEW,
        FACT_TARGET_ROLLUP_VIEW,
        BOUNDARY_PROVINCE_GEOJSON_VIEW,
        INDICATOR_SPATIAL_GEOJSON_VIEW,
        INDICATOR_TIMESERIES_VIEW,
        INDICATOR_REGISTRY_VIEW,
        INDICATOR_LATEST_VALUE_VIEW,
        FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW,
        INDICATOR_READINESS_SUMMARY_VIEW,
        SPATIAL_UNITS_GEOJSON_VIEW,
        INDICATOR_SPATIAL_FEATURES_GEOJSON_VIEW,
    ]


def create_analytics_views() -> list[str]:
    statements = _analytics_view_statements()
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {ANALYTICS_SCHEMA}")
        for view_name in reversed(analytics_view_names()):
            cursor.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")
        for statement in statements:
            cursor.execute(statement)
    return analytics_view_names()


def grant_superset_read_only(*, role_name: str, password: str) -> None:
    role_ident = _quote_ident(role_name)
    db_name = connection.settings_dict["NAME"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role_name])
        if cursor.fetchone():
            cursor.execute(f"ALTER ROLE {role_ident} LOGIN PASSWORD %s", [password])
        else:
            cursor.execute(f"CREATE ROLE {role_ident} LOGIN PASSWORD %s", [password])

        cursor.execute(f"REVOKE ALL PRIVILEGES ON DATABASE {_quote_ident(db_name)} FROM {role_ident}")
        cursor.execute(f"GRANT CONNECT ON DATABASE {_quote_ident(db_name)} TO {role_ident}")
        cursor.execute(f"REVOKE ALL ON SCHEMA public FROM {role_ident}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {role_ident}")
        cursor.execute(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {role_ident}")
        cursor.execute(f"GRANT USAGE ON SCHEMA {ANALYTICS_SCHEMA} TO {role_ident}")
        cursor.execute(f"REVOKE CREATE ON SCHEMA {ANALYTICS_SCHEMA} FROM {role_ident}")
        cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {ANALYTICS_SCHEMA} TO {role_ident}")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {ANALYTICS_SCHEMA} GRANT SELECT ON TABLES TO {role_ident}")
        cursor.execute(f"ALTER ROLE {role_ident} SET search_path TO {ANALYTICS_SCHEMA}")


def _quote_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _geojson_sql(column_name: str, *, simplify_tolerance: str | None = None) -> str:
    if GIS_ENABLED:
        geometry_sql = column_name
        if simplify_tolerance is not None:
            geometry_sql = f"ST_SimplifyPreserveTopology({column_name}, {simplify_tolerance})"
        return f"ST_AsGeoJSON({geometry_sql}, 6)"
    return f"CAST({column_name} AS text)"


def _analytics_view_statements() -> Iterable[str]:
    indicator = _table(Indicator)
    national_target = _table(NationalTarget)
    series = _table(IndicatorDataSeries)
    point = _table(IndicatorDataPoint)
    dataset = _table(Dataset)
    dataset_release = _table(DatasetRelease)
    evidence = _table(Evidence)
    indicator_evidence_link = _table(IndicatorEvidenceLink)
    methodology = _table(Methodology)
    methodology_version = _table(MethodologyVersion)
    indicator_methodology_link = _table(IndicatorMethodologyVersionLink)
    framework = _table(Framework)
    framework_target = _table(FrameworkTarget)
    framework_indicator = _table(FrameworkIndicator)
    indicator_framework_link = _table(IndicatorFrameworkIndicatorLink)
    target_framework_link = _table(NationalTargetFrameworkTargetLink)
    spatial_unit = _table(SpatialUnit)
    spatial_unit_type = _table(SpatialUnitType)
    spatial_layer = _table(SpatialLayer)
    spatial_feature = _table(SpatialFeature)
    license_table = _table(License)

    yield f"""
CREATE OR REPLACE VIEW {FACT_INDICATOR_OBSERVATION_VIEW} AS
WITH primary_method AS (
    SELECT DISTINCT ON (link.indicator_id)
        link.indicator_id,
        version.id AS methodology_version_id,
        version.uuid AS methodology_version_uuid,
        version.version AS methodology_version,
        methodology.methodology_code AS methodology_code,
        methodology.title AS methodology_title
    FROM {indicator_methodology_link} link
    JOIN {methodology_version} version
        ON version.id = link.methodology_version_id
    JOIN {methodology} methodology
        ON methodology.id = version.methodology_id
    WHERE link.is_active = TRUE
      AND version.is_active = TRUE
    ORDER BY link.indicator_id, link.is_primary DESC, version.effective_date DESC NULLS LAST, version.id DESC
)
SELECT
    indicator.id AS indicator_id,
    indicator.uuid AS indicator_uuid,
    indicator.code AS indicator_code,
    indicator.title AS indicator_title,
    indicator.visual_pack_id AS indicator_pack_id,
    indicator.indicator_type AS indicator_type,
    indicator.qa_status AS indicator_qa_status,
    indicator.reporting_capability AS indicator_reporting_capability,
    indicator.last_updated_on AS indicator_last_updated_on,
    indicator.coverage_geography AS indicator_coverage_geography,
    indicator.coverage_time_start_year AS indicator_coverage_time_start_year,
    indicator.coverage_time_end_year AS indicator_coverage_time_end_year,
    indicator.spatial_coverage AS indicator_spatial_coverage,
    indicator.temporal_coverage AS indicator_temporal_coverage,
    target.id AS national_target_id,
    target.uuid AS national_target_uuid,
    target.code AS national_target_code,
    target.title AS national_target_title,
    series.id AS series_id,
    series.uuid AS series_uuid,
    series.series_code AS series_code,
    series.title AS series_title,
    series.unit AS series_unit,
    series.value_type AS series_value_type,
    series.methodology AS series_methodology_summary,
    series.source_notes AS series_source_notes,
    dataset.id AS dataset_id,
    dataset.uuid AS dataset_uuid,
    dataset.dataset_code AS dataset_code,
    dataset.title AS dataset_title,
    dataset.source_url AS dataset_source_url,
    dataset.metadata_json AS dataset_metadata_json,
    release.id AS dataset_release_id,
    release.uuid AS dataset_release_uuid,
    release.version AS dataset_release_version,
    release.release_date AS dataset_release_date,
    release.provenance_json AS dataset_release_provenance_json,
    method.methodology_version_id AS methodology_version_id,
    method.methodology_version_uuid AS methodology_version_uuid,
    method.methodology_version AS methodology_version,
    method.methodology_code AS methodology_code,
    method.methodology_title AS methodology_title,
    point.id AS point_id,
    point.uuid AS point_uuid,
    point.year AS year,
    point.value_numeric AS value_numeric,
    point.value_text AS value_text,
    CASE
        WHEN indicator.indicator_type = 'binary' AND point.value_numeric IS NOT NULL
            THEN (point.value_numeric >= 0.5)
        ELSE NULL
    END AS value_boolean,
    COALESCE(point.disaggregation ->> 'category', point.disaggregation ->> 'threat_category', point.value_text, '') AS value_category,
    point.uncertainty AS uncertainty,
    point.source_url AS source_url,
    point.footnote AS footnote,
    point.disaggregation AS disaggregation,
    point.disaggregation ->> 'realm_code' AS realm_code,
    point.disaggregation ->> 'realm_name' AS realm_name,
    point.disaggregation ->> 'biome_code' AS biome_code,
    point.disaggregation ->> 'biome_name' AS biome_name,
    point.disaggregation ->> 'ecoregion_code' AS ecoregion_code,
    point.disaggregation ->> 'ecoregion_name' AS ecoregion_name,
    COALESCE(point.disaggregation ->> 'province_code', spatial_unit.properties ->> 'province_code', spatial_unit.unit_code, '') AS province_code,
    COALESCE(point.disaggregation ->> 'province_name', spatial_unit.name, '') AS province_name,
    point.disaggregation ->> 'municipality_code' AS municipality_code,
    point.disaggregation ->> 'municipality_name' AS municipality_name,
    point.disaggregation ->> 'ecosystem_type' AS ecosystem_type,
    point.disaggregation ->> 'ecosystem_type_label' AS ecosystem_type_label,
    point.disaggregation ->> 'get_code' AS get_code,
    point.disaggregation ->> 'rle_category' AS rle_category,
    point.disaggregation ->> 'rle_category_label' AS rle_category_label,
    point.disaggregation ->> 'epl_category' AS epl_category,
    point.disaggregation ->> 'epl_category_label' AS epl_category_label,
    point.disaggregation ->> 'protection_category' AS protection_category,
    point.disaggregation ->> 'protection_category_label' AS protection_category_label,
    point.disaggregation ->> 'spi_category' AS spi_category,
    point.disaggregation ->> 'spi_category_label' AS spi_category_label,
    COALESCE(point.disaggregation ->> 'category', point.disaggregation ->> 'threat_category', point.value_text, '') AS category,
    COALESCE(point.disaggregation ->> 'category_label', point.disaggregation ->> 'threat_category_label', point.value_text, '') AS category_label,
    point.disaggregation ->> 'pathway' AS pathway,
    point.disaggregation ->> 'pressure_category' AS pressure_category,
    point.disaggregation ->> 'pressure_category_label' AS pressure_category_label,
    point.disaggregation ->> 'target_progress' AS target_progress,
    point.disaggregation ->> 'target_progress_label' AS target_progress_label,
    point.disaggregation ->> 'protected_area_type' AS protected_area_type,
    point.disaggregation ->> 'restoration_status' AS restoration_status,
    point.disaggregation ->> 'restoration_status_label' AS restoration_status_label,
    point.disaggregation ->> 'habitat_index_band' AS habitat_index_band,
    point.disaggregation ->> 'habitat_index_band_label' AS habitat_index_band_label,
    point.disaggregation ->> 'genetic_diversity_band' AS genetic_diversity_band,
    point.disaggregation ->> 'genetic_diversity_band_label' AS genetic_diversity_band_label,
    point.disaggregation ->> 'policy_status' AS policy_status,
    point.disaggregation ->> 'policy_status_label' AS policy_status_label,
    point.disaggregation ->> 'pollution_type' AS pollution_type,
    point.disaggregation ->> 'pollution_type_label' AS pollution_type_label,
    point.disaggregation ->> 'climate_pressure' AS climate_pressure,
    point.disaggregation ->> 'climate_pressure_label' AS climate_pressure_label,
    point.disaggregation ->> 'taxonomy_kingdom' AS taxonomy_kingdom,
    point.disaggregation ->> 'taxonomy_phylum' AS taxonomy_phylum,
    COALESCE(point.disaggregation ->> 'taxonomy_class', point.disaggregation ->> 'class_name') AS taxonomy_class,
    point.disaggregation ->> 'taxonomy_order' AS taxonomy_order,
    point.disaggregation ->> 'taxonomy_family' AS taxonomy_family,
    point.disaggregation ->> 'taxonomy_genus' AS taxonomy_genus,
    COALESCE(point.disaggregation ->> 'taxonomy_species', point.disaggregation ->> 'scientific_name') AS taxonomy_species,
    CASE
        WHEN COALESCE(point.disaggregation ->> 'province_code', spatial_unit.properties ->> 'province_code', spatial_unit.unit_code, '') <> '' THEN 'province'
        WHEN COALESCE(point.disaggregation ->> 'municipality_code', '') <> '' THEN 'municipality'
        WHEN COALESCE(point.disaggregation ->> 'biome_code', '') <> '' THEN 'biome'
        WHEN COALESCE(point.disaggregation ->> 'ecoregion_code', '') <> '' THEN 'ecoregion'
        WHEN COALESCE(point.disaggregation ->> 'realm_code', '') <> '' THEN 'realm'
        ELSE 'national'
    END AS geo_type,
    CASE
        WHEN COALESCE(point.disaggregation ->> 'province_code', spatial_unit.properties ->> 'province_code', spatial_unit.unit_code, '') <> '' THEN COALESCE(point.disaggregation ->> 'province_code', spatial_unit.properties ->> 'province_code', spatial_unit.unit_code, '')
        WHEN COALESCE(point.disaggregation ->> 'municipality_code', '') <> '' THEN point.disaggregation ->> 'municipality_code'
        WHEN COALESCE(point.disaggregation ->> 'biome_code', '') <> '' THEN point.disaggregation ->> 'biome_code'
        WHEN COALESCE(point.disaggregation ->> 'ecoregion_code', '') <> '' THEN point.disaggregation ->> 'ecoregion_code'
        WHEN COALESCE(point.disaggregation ->> 'realm_code', '') <> '' THEN point.disaggregation ->> 'realm_code'
        ELSE 'NATIONAL'
    END AS geo_code,
    CASE
        WHEN COALESCE(point.disaggregation ->> 'province_code', spatial_unit.properties ->> 'province_code', spatial_unit.unit_code, '') <> '' THEN COALESCE(point.disaggregation ->> 'province_name', spatial_unit.name, COALESCE(point.disaggregation ->> 'province_code', spatial_unit.properties ->> 'province_code', spatial_unit.unit_code, ''))
        WHEN COALESCE(point.disaggregation ->> 'municipality_name', '') <> '' THEN point.disaggregation ->> 'municipality_name'
        WHEN COALESCE(point.disaggregation ->> 'biome_name', '') <> '' THEN point.disaggregation ->> 'biome_name'
        WHEN COALESCE(point.disaggregation ->> 'ecoregion_name', '') <> '' THEN point.disaggregation ->> 'ecoregion_name'
        WHEN COALESCE(point.disaggregation ->> 'realm_name', '') <> '' THEN point.disaggregation ->> 'realm_name'
        ELSE 'National'
    END AS geo_name,
    spatial_unit.id AS spatial_unit_id,
    spatial_unit.uuid AS spatial_unit_uuid,
    spatial_unit.unit_code AS spatial_unit_code,
    spatial_unit.name AS spatial_unit_name,
    spatial_unit_type.code AS spatial_unit_type_code,
    spatial_layer.id AS spatial_layer_id,
    spatial_layer.uuid AS spatial_layer_uuid,
    spatial_layer.layer_code AS spatial_layer_code,
    COALESCE(spatial_layer.title, spatial_layer.name) AS spatial_layer_title,
    GREATEST(
        COALESCE(point.updated_at, point.created_at),
        COALESCE(series.updated_at, series.created_at),
        COALESCE(indicator.updated_at, indicator.created_at),
        COALESCE(release.updated_at, release.created_at),
        COALESCE(dataset.updated_at, dataset.created_at)
    ) AS last_updated
FROM {point} point
JOIN {series} series
    ON series.id = point.series_id
JOIN {indicator} indicator
    ON indicator.id = series.indicator_id
JOIN {national_target} target
    ON target.id = indicator.national_target_id
JOIN {dataset_release} release
    ON release.id = point.dataset_release_id
JOIN {dataset} dataset
    ON dataset.id = release.dataset_id
LEFT JOIN primary_method method
    ON method.indicator_id = indicator.id
LEFT JOIN {spatial_unit} spatial_unit
    ON spatial_unit.id = point.spatial_unit_id
LEFT JOIN {spatial_unit_type} spatial_unit_type
    ON spatial_unit_type.id = spatial_unit.unit_type_id
LEFT JOIN {spatial_layer} spatial_layer
    ON spatial_layer.id = COALESCE(point.spatial_layer_id, series.spatial_layer_id)
WHERE series.indicator_id IS NOT NULL
  AND indicator.status = 'published'
  AND indicator.sensitivity = 'public'
  AND indicator.export_approved = TRUE
  AND target.status = 'published'
  AND target.sensitivity = 'public'
  AND series.status = 'published'
  AND series.sensitivity = 'public'
  AND series.export_approved = TRUE
  AND release.status = 'published'
  AND release.sensitivity = 'public'
  AND release.export_approved = TRUE
  AND dataset.status = 'published'
  AND dataset.sensitivity = 'public'
  AND dataset.export_approved = TRUE
"""

    yield f"""
CREATE OR REPLACE VIEW {DIM_INDICATOR_VIEW} AS
WITH point_stats AS (
    SELECT
        indicator_id,
        indicator_uuid,
        COUNT(DISTINCT series_uuid) AS series_count,
        COUNT(*) AS point_count,
        COUNT(DISTINCT dataset_uuid) AS dataset_count,
        COUNT(DISTINCT dataset_release_uuid) AS dataset_release_count,
        MAX(year) AS latest_year,
        MAX(last_updated) AS last_updated
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    GROUP BY indicator_id, indicator_uuid
),
latest_release AS (
    SELECT DISTINCT ON (indicator_uuid)
        indicator_uuid,
        dataset_release_id,
        dataset_release_uuid,
        dataset_release_version,
        dataset_release_date
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    ORDER BY indicator_uuid, dataset_release_date DESC NULLS LAST, year DESC, point_uuid DESC
),
evidence_counts AS (
    SELECT
        indicator.id AS indicator_id,
        COUNT(DISTINCT evidence.id) AS evidence_count
    FROM {indicator} indicator
    LEFT JOIN {indicator_evidence_link} link
        ON link.indicator_id = indicator.id
    LEFT JOIN {evidence} evidence
        ON evidence.id = link.evidence_id
       AND evidence.status = 'published'
       AND evidence.sensitivity = 'public'
       AND evidence.export_approved = TRUE
    WHERE indicator.status = 'published'
      AND indicator.sensitivity = 'public'
      AND indicator.export_approved = TRUE
    GROUP BY indicator.id
)
SELECT DISTINCT
    fact.indicator_id,
    fact.indicator_uuid,
    fact.indicator_code,
    fact.indicator_title,
    fact.indicator_pack_id,
    fact.indicator_type,
    fact.indicator_qa_status,
    fact.indicator_reporting_capability,
    fact.indicator_last_updated_on,
    fact.indicator_coverage_geography,
    fact.indicator_coverage_time_start_year,
    fact.indicator_coverage_time_end_year,
    fact.indicator_spatial_coverage,
    fact.indicator_temporal_coverage,
    fact.national_target_id,
    fact.national_target_uuid,
    fact.national_target_code,
    fact.national_target_title,
    stats.series_count,
    stats.point_count,
    stats.dataset_count,
    stats.dataset_release_count,
    stats.latest_year,
    COALESCE(evidence_counts.evidence_count, 0) AS evidence_count,
    latest_release.dataset_release_id AS latest_dataset_release_id,
    latest_release.dataset_release_uuid AS latest_dataset_release_uuid,
    latest_release.dataset_release_version AS latest_dataset_release_version,
    latest_release.dataset_release_date AS latest_dataset_release_date,
    stats.last_updated
FROM {FACT_INDICATOR_OBSERVATION_VIEW} fact
JOIN point_stats stats
    ON stats.indicator_id = fact.indicator_id
LEFT JOIN latest_release
    ON latest_release.indicator_uuid = fact.indicator_uuid
LEFT JOIN evidence_counts
    ON evidence_counts.indicator_id = fact.indicator_id
"""

    yield f"""
CREATE OR REPLACE VIEW {DIM_FRAMEWORK_TARGET_VIEW} AS
SELECT DISTINCT
    dim_indicator.indicator_id,
    dim_indicator.indicator_uuid,
    dim_indicator.indicator_code,
    dim_indicator.indicator_title,
    dim_indicator.national_target_id,
    dim_indicator.national_target_uuid,
    dim_indicator.national_target_code,
    dim_indicator.national_target_title,
    framework.id AS framework_id,
    framework.uuid AS framework_uuid,
    framework.code AS framework_code,
    framework.title AS framework_title,
    framework_target.id AS framework_target_id,
    framework_target.uuid AS framework_target_uuid,
    framework_target.code AS framework_target_code,
    framework_target.title AS framework_target_title,
    framework_indicator.id AS framework_indicator_id,
    framework_indicator.uuid AS framework_indicator_uuid,
    framework_indicator.code AS framework_indicator_code,
    framework_indicator.title AS framework_indicator_title,
    target_link.relation_type AS target_relation_type,
    target_link.confidence AS target_confidence,
    target_link.source AS target_source,
    indicator_link.relation_type AS indicator_relation_type,
    indicator_link.confidence AS indicator_confidence,
    indicator_link.source AS indicator_source,
    GREATEST(
        COALESCE(target_link.updated_at, target_link.created_at),
        COALESCE(indicator_link.updated_at, indicator_link.created_at),
        COALESCE(framework_target.updated_at, framework_target.created_at),
        COALESCE(framework.updated_at, framework.created_at)
    ) AS last_updated
FROM {DIM_INDICATOR_VIEW} dim_indicator
JOIN {target_framework_link} target_link
    ON target_link.national_target_id = dim_indicator.national_target_id
   AND target_link.is_active = TRUE
JOIN {framework_target} framework_target
    ON framework_target.id = target_link.framework_target_id
JOIN {framework} framework
    ON framework.id = framework_target.framework_id
LEFT JOIN {indicator_framework_link} indicator_link
    ON indicator_link.indicator_id = dim_indicator.indicator_id
   AND indicator_link.is_active = TRUE
LEFT JOIN {framework_indicator} framework_indicator
    ON framework_indicator.id = indicator_link.framework_indicator_id
   AND framework_indicator.framework_id = framework.id
WHERE framework.status = 'published'
  AND framework.sensitivity = 'public'
  AND framework_target.status = 'published'
  AND framework_target.sensitivity = 'public'
  AND (
        framework_indicator.id IS NULL
        OR (
            framework_indicator.status = 'published'
            AND framework_indicator.sensitivity = 'public'
        )
      )
"""

    yield f"""
CREATE OR REPLACE VIEW {DIM_GEOGRAPHY_VIEW} AS
WITH observed AS (
    SELECT DISTINCT
        'geo:province:' || province_code AS geography_key,
        'province' AS geography_type,
        province_code AS geography_code,
        province_name AS geography_name,
        spatial_unit_uuid,
        spatial_unit_code,
        spatial_unit_name,
        spatial_unit_type_code,
        NULL::numeric AS area_km2,
        'fact' AS source_rank
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    WHERE province_code <> ''
    UNION ALL
    SELECT DISTINCT
        'geo:biome:' || biome_code AS geography_key,
        'biome' AS geography_type,
        biome_code AS geography_code,
        biome_name AS geography_name,
        spatial_unit_uuid,
        spatial_unit_code,
        spatial_unit_name,
        spatial_unit_type_code,
        NULL::numeric AS area_km2,
        'fact' AS source_rank
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    WHERE biome_code <> ''
    UNION ALL
    SELECT DISTINCT
        'geo:ecoregion:' || ecoregion_code AS geography_key,
        'ecoregion' AS geography_type,
        ecoregion_code AS geography_code,
        ecoregion_name AS geography_name,
        spatial_unit_uuid,
        spatial_unit_code,
        spatial_unit_name,
        spatial_unit_type_code,
        NULL::numeric AS area_km2,
        'fact' AS source_rank
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    WHERE ecoregion_code <> ''
    UNION ALL
    SELECT DISTINCT
        'geo:realm:' || realm_code AS geography_key,
        'realm' AS geography_type,
        realm_code AS geography_code,
        realm_name AS geography_name,
        spatial_unit_uuid,
        spatial_unit_code,
        spatial_unit_name,
        spatial_unit_type_code,
        NULL::numeric AS area_km2,
        'fact' AS source_rank
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    WHERE realm_code <> ''
    UNION ALL
    SELECT DISTINCT
        'geo:national:NATIONAL' AS geography_key,
        'national' AS geography_type,
        'NATIONAL' AS geography_code,
        'National' AS geography_name,
        NULL::uuid AS spatial_unit_uuid,
        NULL::varchar AS spatial_unit_code,
        NULL::varchar AS spatial_unit_name,
        NULL::varchar AS spatial_unit_type_code,
        NULL::numeric AS area_km2,
        'fact' AS source_rank
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
),
spatial_observed AS (
    SELECT
        'geo:province:' || COALESCE(spatial_unit.properties ->> 'province_code', spatial_unit.unit_code) AS geography_key,
        'province' AS geography_type,
        COALESCE(spatial_unit.properties ->> 'province_code', spatial_unit.unit_code) AS geography_code,
        spatial_unit.name AS geography_name,
        spatial_unit.uuid AS spatial_unit_uuid,
        spatial_unit.unit_code AS spatial_unit_code,
        spatial_unit.name AS spatial_unit_name,
        spatial_unit_type.code AS spatial_unit_type_code,
        spatial_unit.area_km2 AS area_km2,
        'spatial' AS source_rank
    FROM {spatial_unit} spatial_unit
    JOIN {spatial_unit_type} spatial_unit_type
        ON spatial_unit_type.id = spatial_unit.unit_type_id
    WHERE spatial_unit.is_active = TRUE
      AND spatial_unit.sensitivity = 'public'
      AND spatial_unit_type.code = 'PROVINCE'
),
combined AS (
    SELECT * FROM spatial_observed
    UNION ALL
    SELECT * FROM observed
)
SELECT DISTINCT ON (geography_key)
    geography_key,
    geography_type,
    geography_code,
    geography_name,
    CASE
        WHEN geography_type = 'province' THEN 'geo:national:NATIONAL'
        ELSE NULL
    END AS parent_geography_key,
    spatial_unit_uuid,
    spatial_unit_code,
    spatial_unit_name,
    spatial_unit_type_code,
    area_km2
FROM combined
ORDER BY geography_key, CASE WHEN source_rank = 'spatial' THEN 0 ELSE 1 END
"""

    yield f"""
CREATE OR REPLACE VIEW {DIM_DATASET_RELEASE_VIEW} AS
SELECT DISTINCT
    fact.dataset_id,
    fact.dataset_uuid,
    fact.dataset_code,
    fact.dataset_title,
    fact.dataset_source_url,
    fact.dataset_metadata_json,
    fact.dataset_release_id,
    fact.dataset_release_uuid,
    fact.dataset_release_version,
    fact.dataset_release_date,
    fact.dataset_release_provenance_json,
    license.code AS license_code,
    license.title AS license_title,
    dataset.status AS dataset_status,
    dataset.sensitivity AS dataset_sensitivity,
    dataset.export_approved AS dataset_export_approved,
    release.status AS dataset_release_status,
    release.sensitivity AS dataset_release_sensitivity,
    release.export_approved AS dataset_release_export_approved,
    GREATEST(
        COALESCE(dataset.updated_at, dataset.created_at),
        COALESCE(release.updated_at, release.created_at)
    ) AS last_updated
FROM {FACT_INDICATOR_OBSERVATION_VIEW} fact
JOIN {dataset} dataset
    ON dataset.id = fact.dataset_id
JOIN {dataset_release} release
    ON release.id = fact.dataset_release_id
LEFT JOIN {license_table} license
    ON license.id = dataset.license_id
"""

    yield f"""
CREATE OR REPLACE VIEW {DIM_METHOD_VERSION_VIEW} AS
SELECT DISTINCT
    fact.methodology_version_id,
    fact.methodology_version_uuid,
    fact.methodology_code,
    fact.methodology_title,
    fact.methodology_version,
    version.status AS methodology_status,
    version.effective_date AS methodology_effective_date,
    version.approval_body AS methodology_approval_body,
    version.peer_reviewed AS methodology_peer_reviewed,
    version.is_active AS methodology_is_active,
    COALESCE(version.updated_at, version.created_at) AS last_updated
FROM {FACT_INDICATOR_OBSERVATION_VIEW} fact
JOIN {methodology_version} version
    ON version.id = fact.methodology_version_id
WHERE fact.methodology_version_id IS NOT NULL
"""

    yield f"""
CREATE OR REPLACE VIEW {FACT_READINESS_VIEW} AS
WITH methodology_stats AS (
    SELECT
        indicator_uuid,
        BOOL_OR(methodology_version_uuid IS NOT NULL) AS has_primary_methodology
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    GROUP BY indicator_uuid
),
framework_stats AS (
    SELECT
        indicator_uuid,
        COUNT(*) AS framework_link_count
    FROM {DIM_FRAMEWORK_TARGET_VIEW}
    GROUP BY indicator_uuid
)
SELECT
    dim_indicator.indicator_id,
    dim_indicator.indicator_uuid,
    dim_indicator.indicator_code,
    dim_indicator.indicator_title,
    dim_indicator.indicator_pack_id,
    dim_indicator.national_target_id,
    dim_indicator.national_target_uuid,
    dim_indicator.national_target_code,
    dim_indicator.national_target_title,
    dim_indicator.series_count,
    dim_indicator.point_count,
    dim_indicator.dataset_count,
    dim_indicator.dataset_release_count,
    dim_indicator.evidence_count,
    COALESCE(methodology_stats.has_primary_methodology, FALSE) AS has_primary_methodology,
    COALESCE(framework_stats.framework_link_count, 0) AS framework_link_count,
    dim_indicator.latest_year,
    dim_indicator.latest_dataset_release_date,
    dim_indicator.last_updated,
    CASE
        WHEN dim_indicator.point_count > 0
         AND dim_indicator.dataset_release_count > 0
         AND dim_indicator.evidence_count > 0
         AND COALESCE(methodology_stats.has_primary_methodology, FALSE)
            THEN 'ready'
        WHEN dim_indicator.point_count > 0
            THEN 'partial'
        ELSE 'not_ready'
    END AS readiness_state
FROM {DIM_INDICATOR_VIEW} dim_indicator
LEFT JOIN methodology_stats
    ON methodology_stats.indicator_uuid = dim_indicator.indicator_uuid
LEFT JOIN framework_stats
    ON framework_stats.indicator_uuid = dim_indicator.indicator_uuid
"""

    yield f"""
CREATE OR REPLACE VIEW {FACT_TARGET_ROLLUP_VIEW} AS
WITH latest_release AS (
    SELECT
        indicator_uuid,
        MAX(dataset_release_date) AS dataset_release_date
    FROM {FACT_INDICATOR_OBSERVATION_VIEW}
    GROUP BY indicator_uuid
),
latest_year AS (
    SELECT
        fact.indicator_uuid,
        MAX(fact.year) AS year
    FROM {FACT_INDICATOR_OBSERVATION_VIEW} fact
    JOIN latest_release latest_release
        ON latest_release.indicator_uuid = fact.indicator_uuid
       AND COALESCE(latest_release.dataset_release_date, DATE '1900-01-01') = COALESCE(fact.dataset_release_date, DATE '1900-01-01')
    GROUP BY fact.indicator_uuid
),
latest_indicator_numeric AS (
    SELECT
        fact.indicator_uuid,
        AVG(fact.value_numeric) AS avg_latest_numeric_value,
        SUM(fact.value_numeric) AS sum_latest_numeric_value,
        COUNT(*) AS latest_observation_count,
        MAX(fact.year) AS latest_year,
        MAX(fact.dataset_release_date) AS latest_dataset_release_date,
        MAX(fact.last_updated) AS last_updated
    FROM {FACT_INDICATOR_OBSERVATION_VIEW} fact
    JOIN latest_release latest_release
        ON latest_release.indicator_uuid = fact.indicator_uuid
       AND COALESCE(latest_release.dataset_release_date, DATE '1900-01-01') = COALESCE(fact.dataset_release_date, DATE '1900-01-01')
    JOIN latest_year latest_year
        ON latest_year.indicator_uuid = fact.indicator_uuid
       AND latest_year.year = fact.year
    GROUP BY fact.indicator_uuid
)
SELECT
    dim_framework_target.framework_uuid,
    dim_framework_target.framework_code,
    dim_framework_target.framework_title,
    dim_framework_target.framework_target_uuid,
    dim_framework_target.framework_target_code,
    dim_framework_target.framework_target_title,
    dim_framework_target.national_target_uuid,
    dim_framework_target.national_target_code,
    dim_framework_target.national_target_title,
    COUNT(DISTINCT dim_framework_target.indicator_uuid) AS indicator_count,
    SUM(CASE WHEN fact_readiness.readiness_state = 'ready' THEN 1 ELSE 0 END) AS ready_indicator_count,
    AVG(latest_indicator_numeric.avg_latest_numeric_value) AS avg_latest_numeric_value,
    SUM(latest_indicator_numeric.sum_latest_numeric_value) AS sum_latest_numeric_value,
    SUM(latest_indicator_numeric.latest_observation_count) AS latest_observation_count,
    MAX(latest_indicator_numeric.latest_year) AS latest_year,
    MAX(latest_indicator_numeric.latest_dataset_release_date) AS latest_dataset_release_date,
    MAX(latest_indicator_numeric.last_updated) AS last_updated
FROM {DIM_FRAMEWORK_TARGET_VIEW} dim_framework_target
LEFT JOIN {FACT_READINESS_VIEW} fact_readiness
    ON fact_readiness.indicator_uuid = dim_framework_target.indicator_uuid
LEFT JOIN latest_indicator_numeric
    ON latest_indicator_numeric.indicator_uuid = dim_framework_target.indicator_uuid
GROUP BY
    dim_framework_target.framework_uuid,
    dim_framework_target.framework_code,
    dim_framework_target.framework_title,
    dim_framework_target.framework_target_uuid,
    dim_framework_target.framework_target_code,
    dim_framework_target.framework_target_title,
    dim_framework_target.national_target_uuid,
    dim_framework_target.national_target_code,
    dim_framework_target.national_target_title
"""

    yield f"""
CREATE OR REPLACE VIEW {BOUNDARY_PROVINCE_GEOJSON_VIEW} AS
SELECT
    spatial_unit.uuid AS spatial_unit_uuid,
    COALESCE(spatial_unit.properties ->> 'province_code', spatial_unit.unit_code) AS province_code,
    spatial_unit.name AS province_name,
    spatial_unit.area_km2,
    {_geojson_sql("spatial_unit.geom", simplify_tolerance="0.01")} AS geojson
FROM {spatial_unit} spatial_unit
JOIN {spatial_unit_type} spatial_unit_type
    ON spatial_unit_type.id = spatial_unit.unit_type_id
WHERE spatial_unit.is_active = TRUE
  AND spatial_unit.sensitivity = 'public'
  AND spatial_unit_type.code = 'PROVINCE'
  AND spatial_unit.geom IS NOT NULL
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_SPATIAL_GEOJSON_VIEW} AS
SELECT
    spatial_feature.uuid AS spatial_feature_uuid,
    spatial_feature.feature_id,
    spatial_feature.feature_key,
    spatial_feature.name AS feature_name,
    spatial_feature.province_code,
    spatial_feature.year,
    spatial_feature.properties,
    spatial_layer.uuid AS spatial_layer_uuid,
    spatial_layer.layer_code AS spatial_layer_code,
    COALESCE(spatial_layer.title, spatial_layer.name) AS spatial_layer_title,
    indicator.uuid AS indicator_uuid,
    indicator.code AS indicator_code,
    indicator.title AS indicator_title,
    {_geojson_sql("spatial_feature.geom", simplify_tolerance="0.001")} AS geojson
FROM {spatial_feature} spatial_feature
JOIN {spatial_layer} spatial_layer
    ON spatial_layer.id = spatial_feature.layer_id
LEFT JOIN {indicator} indicator
    ON indicator.id = COALESCE(spatial_feature.indicator_id, spatial_layer.indicator_id)
WHERE spatial_layer.is_active = TRUE
  AND spatial_layer.is_public = TRUE
  AND spatial_layer.export_approved = TRUE
  AND spatial_layer.sensitivity = 'public'
  AND spatial_feature.geom IS NOT NULL
  AND (
        indicator.id IS NULL
        OR (
            indicator.status = 'published'
            AND indicator.sensitivity = 'public'
            AND indicator.export_approved = TRUE
        )
      )
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_TIMESERIES_VIEW} AS
SELECT
    indicator_uuid,
    indicator_code,
    indicator_title,
    indicator_pack_id,
    indicator_type,
    indicator_qa_status,
    indicator_reporting_capability,
    indicator_last_updated_on,
    indicator_coverage_geography,
    indicator_coverage_time_start_year,
    indicator_coverage_time_end_year,
    indicator_spatial_coverage,
    indicator_temporal_coverage,
    national_target_uuid,
    national_target_code,
    national_target_title,
    series_uuid,
    series_code,
    series_title,
    series_unit,
    series_value_type,
    series_methodology_summary,
    series_source_notes,
    dataset_uuid,
    dataset_code,
    dataset_title,
    dataset_source_url,
    dataset_metadata_json,
    dataset_release_uuid,
    dataset_release_version,
    dataset_release_date,
    dataset_release_provenance_json,
    methodology_version_uuid,
    methodology_version,
    methodology_code,
    methodology_title,
    point_uuid,
    year,
    value_numeric,
    value_text,
    uncertainty,
    source_url,
    footnote,
    disaggregation,
    realm_code,
    realm_name,
    biome_code,
    biome_name,
    ecoregion_code,
    ecoregion_name,
    province_code,
    province_name,
    municipality_code,
    municipality_name,
    ecosystem_type,
    ecosystem_type_label,
    get_code,
    rle_category,
    rle_category_label,
    epl_category,
    epl_category_label,
    protection_category,
    protection_category_label,
    category,
    category_label,
    taxonomy_kingdom,
    taxonomy_phylum,
    taxonomy_class,
    taxonomy_order,
    taxonomy_family,
    taxonomy_genus,
    taxonomy_species,
    spatial_unit_uuid,
    spatial_unit_code,
    spatial_unit_name,
    spatial_unit_type_code,
    spatial_layer_uuid,
    spatial_layer_code,
    spatial_layer_title,
    point_id,
    dataset_release_id,
    methodology_version_id,
    value_boolean,
    value_category,
    pathway,
    pressure_category,
    pressure_category_label,
    target_progress,
    target_progress_label,
    protected_area_type,
    restoration_status,
    restoration_status_label,
    habitat_index_band,
    habitat_index_band_label,
    genetic_diversity_band,
    genetic_diversity_band_label,
    policy_status,
    policy_status_label,
    pollution_type,
    pollution_type_label,
    climate_pressure,
    climate_pressure_label,
    geo_type,
    geo_code,
    geo_name,
    last_updated
FROM {FACT_INDICATOR_OBSERVATION_VIEW}
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_REGISTRY_VIEW} AS
SELECT
    indicator_uuid,
    indicator_code,
    indicator_title,
    indicator_pack_id,
    indicator_type,
    indicator_qa_status,
    indicator_reporting_capability,
    indicator_last_updated_on,
    national_target_uuid,
    national_target_code,
    national_target_title,
    series_count,
    point_count,
    dataset_count,
    dataset_release_count,
    latest_year,
    evidence_count,
    latest_dataset_release_uuid,
    latest_dataset_release_version,
    latest_dataset_release_date,
    last_updated
FROM {DIM_INDICATOR_VIEW}
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_LATEST_VALUE_VIEW} AS
WITH ranked AS (
    SELECT
        timeseries.*,
        ROW_NUMBER() OVER (
            PARTITION BY timeseries.indicator_uuid
            ORDER BY
                timeseries.dataset_release_date DESC NULLS LAST,
                timeseries.year DESC,
                CASE WHEN timeseries.geo_type = 'national' THEN 0 ELSE 1 END,
                timeseries.point_id DESC
        ) AS row_number
    FROM {INDICATOR_TIMESERIES_VIEW} timeseries
)
SELECT *
FROM ranked
WHERE row_number = 1
"""

    yield f"""
CREATE OR REPLACE VIEW {FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW} AS
SELECT
    indicator_uuid,
    indicator_code,
    indicator_title,
    national_target_uuid,
    national_target_code,
    national_target_title,
    framework_uuid,
    framework_code,
    framework_title,
    framework_target_uuid,
    framework_target_code,
    framework_target_title,
    framework_indicator_uuid,
    framework_indicator_code,
    framework_indicator_title,
    target_relation_type,
    target_confidence,
    target_source,
    indicator_relation_type,
    indicator_confidence,
    indicator_source,
    last_updated
FROM {DIM_FRAMEWORK_TARGET_VIEW}
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_READINESS_SUMMARY_VIEW} AS
SELECT
    indicator_uuid,
    indicator_code,
    indicator_title,
    indicator_pack_id,
    national_target_code,
    national_target_title,
    series_count,
    point_count,
    dataset_count,
    dataset_release_count,
    evidence_count,
    has_primary_methodology,
    framework_link_count,
    latest_year,
    latest_dataset_release_date,
    readiness_state,
    last_updated
FROM {FACT_READINESS_VIEW}
"""

    yield f"""
CREATE OR REPLACE VIEW {SPATIAL_UNITS_GEOJSON_VIEW} AS
SELECT
    spatial_unit.uuid AS spatial_unit_uuid,
    spatial_unit.unit_code,
    spatial_unit.name,
    spatial_unit_type.code AS unit_type_code,
    spatial_unit.area_km2,
    spatial_unit.properties,
    {_geojson_sql("spatial_unit.geom", simplify_tolerance="0.01")} AS geojson
FROM {spatial_unit} spatial_unit
JOIN {spatial_unit_type} spatial_unit_type
    ON spatial_unit_type.id = spatial_unit.unit_type_id
WHERE spatial_unit.is_active = TRUE
  AND spatial_unit.sensitivity = 'public'
  AND spatial_unit.geom IS NOT NULL
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_SPATIAL_FEATURES_GEOJSON_VIEW} AS
SELECT *
FROM {INDICATOR_SPATIAL_GEOJSON_VIEW}
"""
