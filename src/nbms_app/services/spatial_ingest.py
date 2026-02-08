from __future__ import annotations

import hashlib
import re
import subprocess
import uuid
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

from nbms_app.models import SpatialIngestionRun, SpatialIngestionStatus, SpatialLayer, SpatialLayerSourceType
from nbms_app.services.audit import record_audit_event
from nbms_app.spatial_fields import GIS_ENABLED


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _db_conn_string():
    db = settings.DATABASES["default"]
    return (
        "PG:"
        f"host={db.get('HOST') or 'localhost'} "
        f"port={db.get('PORT') or 5432} "
        f"dbname={db.get('NAME')} "
        f"user={db.get('USER')} "
        f"password={db.get('PASSWORD') or ''}"
    )


def _detect_source_format(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".geojson" or suffix == ".json":
        return "GeoJSON"
    if suffix == ".gpkg":
        return "GPKG"
    if suffix == ".shp":
        return "ESRI Shapefile"
    if suffix == ".zip":
        return "ESRI Shapefile"
    return "UNKNOWN"


def _ogr_source_path(path: Path):
    if path.suffix.lower() == ".zip":
        return f"/vsizip/{path.as_posix()}"
    return path.as_posix()


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str) -> str:
    if not _IDENTIFIER_RE.match(value):
        raise RuntimeError(f"Unsafe SQL identifier: {value}")
    return value


def _geometry_column(cursor, table_name: str) -> str:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND udt_name = 'geometry'
        ORDER BY CASE WHEN table_schema = 'public' THEN 0 ELSE 1 END, ordinal_position
        LIMIT 1
        """,
        [table_name],
    )
    row = cursor.fetchone()
    if row and row[0]:
        return _safe_identifier(row[0])

    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name IN ('geom', 'wkb_geometry', 'geometry')
        ORDER BY ordinal_position
        LIMIT 1
        """,
        [table_name],
    )
    row = cursor.fetchone()
    if row and row[0]:
        return _safe_identifier(row[0])
    return "geom"


def _parse_clip_bbox(value):
    if not value:
        return None
    parts = [item.strip() for item in str(value).split(",")]
    if len(parts) != 4:
        return None
    try:
        minx, miny, maxx, maxy = tuple(float(item) for item in parts)
    except ValueError:
        return None
    if minx >= maxx or miny >= maxy:
        return None
    return minx, miny, maxx, maxy


COUNTRY_FILTER_FIELDS = [
    "adm0_a3",
    "ADM0_A3",
    "adm0_a3_us",
    "ADM0_A3_US",
    "iso_a3",
    "ISO_A3",
    "sov_a3",
    "SOV_A3",
    "country",
    "COUNTRY",
    "admin",
    "ADMIN",
    "name_en",
    "NAME_EN",
]

COUNTRY_NAME_ALIASES = {
    "ZAF": ["SOUTH AFRICA", "REPUBLIC OF SOUTH AFRICA"],
}


def _country_filter_values(code: str):
    clean = (code or "").strip().upper()
    if not clean:
        return []
    values = {clean}
    if clean == "ZAF":
        values.add("ZA")
    values.update(COUNTRY_NAME_ALIASES.get(clean, []))
    return sorted(values)


def ingest_spatial_file(
    *,
    layer: SpatialLayer,
    file_path: str,
    source_filename: str,
    user=None,
    source_layer_name=None,
    source_storage_path="",
    source=None,
    clip_bbox=None,
    country_iso3=None,
):
    run = SpatialIngestionRun.objects.create(
        run_id=f"spatial-{uuid.uuid4().hex[:12]}",
        layer=layer,
        source=source,
        status=SpatialIngestionStatus.RUNNING,
        source_filename=source_filename or "",
        source_storage_path=source_storage_path or "",
        started_at=timezone.now(),
        triggered_by=user if getattr(user, "is_authenticated", False) else None,
    )
    path = Path(file_path)
    run.source_format = _detect_source_format(path)
    run.source_hash = _sha256_file(path)
    run.source_layer_name = source_layer_name or ""
    run.save(update_fields=["source_format", "source_hash", "source_layer_name", "updated_at"])

    tmp_table = f"tmp_spatial_ingest_{layer.id}_{uuid.uuid4().hex[:8]}"
    source_path = _ogr_source_path(path)
    cmd = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        _db_conn_string(),
        source_path,
        "-nln",
        tmp_table,
        "-t_srs",
        "EPSG:4326",
        "-nlt",
        "PROMOTE_TO_MULTI",
        "-lco",
        "GEOMETRY_NAME=geom",
        "-overwrite",
    ]
    if source_layer_name:
        cmd.append(source_layer_name)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "ogr2ogr failed")

        with connection.cursor() as cursor:
            geom_col = _geometry_column(cursor, tmp_table)
            cursor.execute(f"SELECT COUNT(*) FROM {tmp_table} WHERE {geom_col} IS NULL OR NOT ST_IsValid({geom_col})")
            invalid_before = int(cursor.fetchone()[0] or 0)

            cursor.execute(
                f"UPDATE {tmp_table} "
                f"SET {geom_col} = ST_MakeValid({geom_col}) "
                f"WHERE {geom_col} IS NOT NULL AND NOT ST_IsValid({geom_col})"
            )
            cursor.execute(f"SELECT COUNT(*) FROM {tmp_table} WHERE {geom_col} IS NULL OR NOT ST_IsValid({geom_col})")
            invalid_after = int(cursor.fetchone()[0] or 0)
            if invalid_after:
                raise RuntimeError(f"{invalid_after} features are invalid after ST_MakeValid.")

            cursor.execute(
                """
                DELETE FROM nbms_app_spatialfeature
                WHERE layer_id = %s
                """,
                [layer.id],
            )

            filter_sql = [f"t.{geom_col} IS NOT NULL"]
            filter_params = []

            clip_values = _parse_clip_bbox(clip_bbox)
            if clip_values and GIS_ENABLED:
                filter_sql.append(
                    "ST_Intersects("
                    f"t.{geom_col}, ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
                    ")"
                )
                filter_params.extend([*clip_values])

            country_values = _country_filter_values(country_iso3)
            if country_values:
                country_expr = "UPPER(COALESCE(" + ", ".join(
                    [f"NULLIF((to_jsonb(t)->>'{field}'), '')" for field in COUNTRY_FILTER_FIELDS]
                ) + "))"
                placeholders = ", ".join(["%s"] * len(country_values))
                filter_sql.append(f"{country_expr} IN ({placeholders})")
                filter_params.extend(country_values)

            where_sql = f"WHERE {' AND '.join(filter_sql)}" if filter_sql else ""

            insert_sql = f"""
                INSERT INTO nbms_app_spatialfeature
                (
                    created_at,
                    updated_at,
                    uuid,
                    layer_id,
                    feature_id,
                    feature_key,
                    name,
                    province_code,
                    year,
                    properties,
                    properties_json,
                    geom,
                    geometry_json,
                    minx,
                    miny,
                    maxx,
                    maxy
                )
                SELECT
                    NOW(),
                    NOW(),
                    (
                        substr(md5(random()::text || clock_timestamp()::text), 1, 8) || '-' ||
                        substr(md5(random()::text || clock_timestamp()::text), 9, 4) || '-' ||
                        substr(md5(random()::text || clock_timestamp()::text), 13, 4) || '-' ||
                        substr(md5(random()::text || clock_timestamp()::text), 17, 4) || '-' ||
                        substr(md5(random()::text || clock_timestamp()::text), 21, 12)
                    )::uuid,
                    %s,
                    COALESCE(NULLIF((to_jsonb(t)->>'id'), ''), md5((row_number() OVER ())::text || random()::text)),
                    COALESCE(NULLIF((to_jsonb(t)->>'id'), ''), md5((row_number() OVER ())::text || random()::text)),
                    COALESCE(NULLIF((to_jsonb(t)->>'name'), ''), NULLIF((to_jsonb(t)->>'NAME'), ''), ''),
                    COALESCE(NULLIF((to_jsonb(t)->>'province_code'), ''), NULLIF((to_jsonb(t)->>'province'), ''), ''),
                    NULLIF((to_jsonb(t)->>'year'), '')::int,
                    (jsonb_strip_nulls(to_jsonb(t) - %s))::jsonb,
                    (jsonb_strip_nulls(to_jsonb(t) - %s))::jsonb,
                    t.{geom_col},
                    ST_AsGeoJSON(t.{geom_col})::jsonb,
                    ST_XMin(t.{geom_col}),
                    ST_YMin(t.{geom_col}),
                    ST_XMax(t.{geom_col}),
                    ST_YMax(t.{geom_col})
                FROM {tmp_table} t
                {where_sql}
            """
            cursor.execute(insert_sql, [layer.id, geom_col, geom_col, *filter_params])
            inserted = cursor.rowcount
            cursor.execute(f"DROP TABLE IF EXISTS {tmp_table}")

        run.status = SpatialIngestionStatus.SUCCEEDED
        run.rows_ingested = max(0, inserted)
        run.invalid_geom_before_fix = invalid_before
        run.invalid_geom_after_fix = invalid_after
        run.report_json = {
            "ogr2ogr_stdout": proc.stdout[-2000:],
            "ogr2ogr_stderr": proc.stderr[-2000:],
            "country_iso3": (country_iso3 or "").strip().upper(),
        }
        run.finished_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "rows_ingested",
                "invalid_geom_before_fix",
                "invalid_geom_after_fix",
                "report_json",
                "finished_at",
                "updated_at",
            ]
        )

        layer.source_type = SpatialLayerSourceType.UPLOADED_FILE
        layer.data_ref = "nbms_app_spatialfeature"
        layer.source_file_hash = run.source_hash
        layer.latest_ingestion_run = run
        layer.save(update_fields=["source_type", "data_ref", "source_file_hash", "latest_ingestion_run", "updated_at"])

        record_audit_event(
            user,
            "spatial_ingest",
            layer,
            metadata={
                "run_id": run.run_id,
                "rows_ingested": run.rows_ingested,
                "source_filename": run.source_filename,
                "source_hash": run.source_hash,
            },
        )
        return run
    except Exception as exc:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {tmp_table}")
        except Exception:
            pass
        run.status = SpatialIngestionStatus.FAILED
        run.report_json = {"error": str(exc)}
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "report_json", "finished_at", "updated_at"])
        record_audit_event(
            user,
            "spatial_ingest_failed",
            layer,
            metadata={"run_id": run.run_id, "error": str(exc)},
        )
        return run
