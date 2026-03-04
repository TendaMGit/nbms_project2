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
    Methodology,
    MethodologyVersion,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    SpatialFeature,
    SpatialLayer,
    SpatialUnit,
    SpatialUnitType,
)


ANALYTICS_SCHEMA = "analytics"
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

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_TIMESERIES_VIEW} AS
WITH primary_method AS (
    SELECT DISTINCT ON (link.indicator_id)
        link.indicator_id,
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
    target.uuid AS national_target_uuid,
    target.code AS national_target_code,
    target.title AS national_target_title,
    series.uuid AS series_uuid,
    series.series_code AS series_code,
    series.title AS series_title,
    series.unit AS series_unit,
    series.value_type AS series_value_type,
    series.methodology AS series_methodology_summary,
    series.source_notes AS series_source_notes,
    dataset.uuid AS dataset_uuid,
    dataset.dataset_code AS dataset_code,
    dataset.title AS dataset_title,
    dataset.source_url AS dataset_source_url,
    dataset.metadata_json AS dataset_metadata_json,
    release.uuid AS dataset_release_uuid,
    release.version AS dataset_release_version,
    release.release_date AS dataset_release_date,
    release.provenance_json AS dataset_release_provenance_json,
    method.methodology_version_uuid AS methodology_version_uuid,
    method.methodology_version AS methodology_version,
    method.methodology_code AS methodology_code,
    method.methodology_title AS methodology_title,
    point.uuid AS point_uuid,
    point.year AS year,
    point.value_numeric AS value_numeric,
    point.value_text AS value_text,
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
    COALESCE(point.disaggregation ->> 'province_code', spatial_unit.unit_code, '') AS province_code,
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
    COALESCE(point.disaggregation ->> 'category', point.disaggregation ->> 'threat_category', point.value_text, '') AS category,
    COALESCE(point.disaggregation ->> 'category_label', point.disaggregation ->> 'threat_category_label', point.value_text, '') AS category_label,
    point.disaggregation ->> 'taxonomy_kingdom' AS taxonomy_kingdom,
    point.disaggregation ->> 'taxonomy_phylum' AS taxonomy_phylum,
    COALESCE(point.disaggregation ->> 'taxonomy_class', point.disaggregation ->> 'class_name') AS taxonomy_class,
    point.disaggregation ->> 'taxonomy_order' AS taxonomy_order,
    point.disaggregation ->> 'taxonomy_family' AS taxonomy_family,
    point.disaggregation ->> 'taxonomy_genus' AS taxonomy_genus,
    COALESCE(point.disaggregation ->> 'taxonomy_species', point.disaggregation ->> 'scientific_name') AS taxonomy_species,
    spatial_unit.uuid AS spatial_unit_uuid,
    spatial_unit.unit_code AS spatial_unit_code,
    spatial_unit.name AS spatial_unit_name,
    spatial_unit_type.code AS spatial_unit_type_code,
    spatial_layer.uuid AS spatial_layer_uuid,
    spatial_layer.layer_code AS spatial_layer_code,
    COALESCE(spatial_layer.title, spatial_layer.name) AS spatial_layer_title
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
CREATE OR REPLACE VIEW {INDICATOR_REGISTRY_VIEW} AS
WITH point_stats AS (
    SELECT
        indicator_uuid,
        COUNT(DISTINCT series_uuid) AS series_count,
        COUNT(*) AS point_count,
        COUNT(DISTINCT dataset_uuid) AS dataset_count,
        COUNT(DISTINCT dataset_release_uuid) AS dataset_release_count,
        MAX(year) AS latest_year
    FROM {INDICATOR_TIMESERIES_VIEW}
    GROUP BY indicator_uuid
),
latest_release AS (
    SELECT DISTINCT ON (indicator_uuid)
        indicator_uuid,
        dataset_release_uuid,
        dataset_release_version,
        dataset_release_date
    FROM {INDICATOR_TIMESERIES_VIEW}
    ORDER BY indicator_uuid, dataset_release_date DESC NULLS LAST, year DESC, point_uuid DESC
),
evidence_counts AS (
    SELECT
        indicator.uuid AS indicator_uuid,
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
    GROUP BY indicator.uuid
)
SELECT DISTINCT
    timeseries.indicator_uuid,
    timeseries.indicator_code,
    timeseries.indicator_title,
    timeseries.indicator_pack_id,
    timeseries.indicator_type,
    timeseries.indicator_qa_status,
    timeseries.indicator_reporting_capability,
    timeseries.indicator_last_updated_on,
    timeseries.national_target_uuid,
    timeseries.national_target_code,
    timeseries.national_target_title,
    stats.series_count,
    stats.point_count,
    stats.dataset_count,
    stats.dataset_release_count,
    stats.latest_year,
    COALESCE(evidence_counts.evidence_count, 0) AS evidence_count,
    latest_release.dataset_release_uuid AS latest_dataset_release_uuid,
    latest_release.dataset_release_version AS latest_dataset_release_version,
    latest_release.dataset_release_date AS latest_dataset_release_date
FROM {INDICATOR_TIMESERIES_VIEW} timeseries
JOIN point_stats stats
    ON stats.indicator_uuid = timeseries.indicator_uuid
LEFT JOIN latest_release
    ON latest_release.indicator_uuid = timeseries.indicator_uuid
LEFT JOIN evidence_counts
    ON evidence_counts.indicator_uuid = timeseries.indicator_uuid
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
                timeseries.point_uuid DESC
        ) AS row_number
    FROM {INDICATOR_TIMESERIES_VIEW} timeseries
)
SELECT *
FROM ranked
WHERE row_number = 1
"""

    yield f"""
CREATE OR REPLACE VIEW {FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW} AS
SELECT DISTINCT
    indicator.uuid AS indicator_uuid,
    indicator.code AS indicator_code,
    indicator.title AS indicator_title,
    target.uuid AS national_target_uuid,
    target.code AS national_target_code,
    target.title AS national_target_title,
    framework.uuid AS framework_uuid,
    framework.code AS framework_code,
    framework.title AS framework_title,
    framework_target.uuid AS framework_target_uuid,
    framework_target.code AS framework_target_code,
    framework_target.title AS framework_target_title,
    framework_indicator.uuid AS framework_indicator_uuid,
    framework_indicator.code AS framework_indicator_code,
    framework_indicator.title AS framework_indicator_title,
    target_link.relation_type AS target_relation_type,
    target_link.confidence AS target_confidence,
    target_link.source AS target_source,
    indicator_link.relation_type AS indicator_relation_type,
    indicator_link.confidence AS indicator_confidence,
    indicator_link.source AS indicator_source
FROM {indicator} indicator
JOIN {national_target} target
    ON target.id = indicator.national_target_id
JOIN {target_framework_link} target_link
    ON target_link.national_target_id = target.id
   AND target_link.is_active = TRUE
JOIN {framework_target} framework_target
    ON framework_target.id = target_link.framework_target_id
JOIN {framework} framework
    ON framework.id = framework_target.framework_id
LEFT JOIN {indicator_framework_link} indicator_link
    ON indicator_link.indicator_id = indicator.id
   AND indicator_link.is_active = TRUE
LEFT JOIN {framework_indicator} framework_indicator
    ON framework_indicator.id = indicator_link.framework_indicator_id
   AND framework_indicator.framework_id = framework.id
WHERE indicator.status = 'published'
  AND indicator.sensitivity = 'public'
  AND indicator.export_approved = TRUE
  AND target.status = 'published'
  AND target.sensitivity = 'public'
  AND framework.status = 'published'
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
CREATE OR REPLACE VIEW {INDICATOR_READINESS_SUMMARY_VIEW} AS
WITH methodology_stats AS (
    SELECT
        indicator_uuid,
        BOOL_OR(methodology_version_uuid IS NOT NULL) AS has_primary_methodology
    FROM {INDICATOR_TIMESERIES_VIEW}
    GROUP BY indicator_uuid
),
framework_stats AS (
    SELECT
        indicator_uuid,
        COUNT(*) AS framework_link_count
    FROM {FRAMEWORK_TARGET_INDICATOR_LINKS_VIEW}
    GROUP BY indicator_uuid
)
SELECT
    registry.indicator_uuid,
    registry.indicator_code,
    registry.indicator_title,
    registry.indicator_pack_id,
    registry.national_target_code,
    registry.national_target_title,
    registry.series_count,
    registry.point_count,
    registry.dataset_count,
    registry.dataset_release_count,
    registry.evidence_count,
    COALESCE(methodology_stats.has_primary_methodology, FALSE) AS has_primary_methodology,
    COALESCE(framework_stats.framework_link_count, 0) AS framework_link_count,
    registry.latest_year,
    registry.latest_dataset_release_date,
    CASE
        WHEN registry.point_count > 0
         AND registry.dataset_release_count > 0
         AND registry.evidence_count > 0
         AND COALESCE(methodology_stats.has_primary_methodology, FALSE)
            THEN 'ready'
        WHEN registry.point_count > 0
            THEN 'partial'
        ELSE 'not_ready'
    END AS readiness_state
FROM {INDICATOR_REGISTRY_VIEW} registry
LEFT JOIN methodology_stats
    ON methodology_stats.indicator_uuid = registry.indicator_uuid
LEFT JOIN framework_stats
    ON framework_stats.indicator_uuid = registry.indicator_uuid
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
    ST_AsGeoJSON(spatial_unit.geom, 6) AS geojson
FROM {spatial_unit} spatial_unit
JOIN {spatial_unit_type} spatial_unit_type
    ON spatial_unit_type.id = spatial_unit.unit_type_id
WHERE spatial_unit.is_active = TRUE
  AND spatial_unit.sensitivity = 'public'
  AND spatial_unit.geom IS NOT NULL
"""

    yield f"""
CREATE OR REPLACE VIEW {INDICATOR_SPATIAL_FEATURES_GEOJSON_VIEW} AS
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
    ST_AsGeoJSON(spatial_feature.geom, 6) AS geojson
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
