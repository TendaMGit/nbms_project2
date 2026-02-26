from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.utils import timezone

from nbms_app.models import (
    Organisation,
    SensitivityLevel,
    SpatialFeature,
    SpatialIngestionStatus,
    SpatialLayer,
    SpatialLayerSourceType,
    SpatialSource,
    SpatialSourceFormat,
    SpatialSourceSyncStatus,
    UpdateFrequency,
)
from nbms_app.services.spatial_ingest import ingest_spatial_file


DEFAULT_SPATIAL_SOURCE_DEFINITIONS = [
    {
        "code": "NE_ADMIN1_ZA",
        "title": "Natural Earth Admin-1 (South Africa subset)",
        "description": "South African provincial/state boundaries from Natural Earth Admin-1.",
        "source_url": "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip",
        "source_format": SpatialSourceFormat.ZIP_SHAPEFILE,
        "source_layer_name": "ne_10m_admin_1_states_provinces",
        "license": "Public Domain",
        "attribution": "Natural Earth",
        "terms_url": "https://www.naturalearthdata.com/about/terms-of-use/",
        "requires_token": False,
        "token_env_var": "",
        "update_frequency": UpdateFrequency.ANNUAL,
        "enabled_by_default": True,
        "source_type": SpatialLayerSourceType.UPLOADED_FILE,
        "layer_code": "ZA_PROVINCES_NE",
        "layer_title": "South Africa Provinces (Natural Earth)",
        "layer_description": "Open baseline for provincial disaggregation and map overlays.",
        "theme": "Admin",
        "default_style_json": {"fillColor": "#7ca982", "lineColor": "#2f5d50", "circleColor": "#1b4332"},
        "sensitivity": SensitivityLevel.PUBLIC,
        "consent_required": False,
        "export_approved": True,
        "is_public": True,
        "publish_to_geoserver": True,
        "clip_bbox": "16.0,-35.5,33.5,-21.0",
        "country_iso3": "ZAF",
    },
    {
        "code": "NE_PROTECTED_LANDS_ZA",
        "title": "DFFE Protected Areas (South Africa public release)",
        "description": "South African Protected Areas Database (SAPAD) public release served by DFFE ArcGIS.",
        "source_url": "https://dpmegis.dpme.gov.za/arcgis/rest/services/Environmental2/MapServer/1/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=pjson",
        "source_format": SpatialSourceFormat.GEOJSON,
        "source_layer_name": "",
        "license": "Public release (DFFE SAPAD) with attribution",
        "attribution": "Department of Forestry, Fisheries and the Environment (DFFE), South Africa",
        "terms_url": "https://dpmegis.dpme.gov.za/arcgis/rest/services/Environmental2/MapServer/1?f=pjson",
        "requires_token": False,
        "token_env_var": "",
        "update_frequency": UpdateFrequency.ANNUAL,
        "enabled_by_default": True,
        "source_type": SpatialLayerSourceType.UPLOADED_FILE,
        "layer_code": "ZA_PROTECTED_AREAS_NE",
        "layer_title": "Protected Areas (Natural Earth)",
        "layer_description": "Protected lands proxy layer used for programme and indicator overlay workflows.",
        "theme": "GBF",
        "default_style_json": {"fillColor": "#2d6a4f", "lineColor": "#1b4332", "circleColor": "#1b4332"},
        "sensitivity": SensitivityLevel.PUBLIC,
        "consent_required": False,
        "export_approved": True,
        "is_public": True,
        "publish_to_geoserver": True,
        "clip_bbox": "16.0,-35.5,33.5,-21.0",
        "country_iso3": "",
    },
    {
        "code": "NE_GEOREGIONS_ZA",
        "title": "Natural Earth Geography Regions (South Africa subset)",
        "description": "Bioregion proxy polygons from Natural Earth geography regions for ecosystem map products.",
        "source_url": "https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_geography_regions_polys.zip",
        "source_format": SpatialSourceFormat.ZIP_SHAPEFILE,
        "source_layer_name": "ne_10m_geography_regions_polys",
        "license": "Public Domain",
        "attribution": "Natural Earth",
        "terms_url": "https://www.naturalearthdata.com/about/terms-of-use/",
        "requires_token": False,
        "token_env_var": "",
        "update_frequency": UpdateFrequency.ANNUAL,
        "enabled_by_default": True,
        "source_type": SpatialLayerSourceType.UPLOADED_FILE,
        "layer_code": "ZA_ECOSYSTEM_PROXY_NE",
        "layer_title": "Ecosystem Regions (Natural Earth Proxy)",
        "layer_description": "Proxy ecosystem-regions layer for NBMS mapping and readiness demonstrations.",
        "theme": "GBF",
        "default_style_json": {"fillColor": "#ff9f1c", "lineColor": "#9d0208", "circleColor": "#9d0208"},
        "sensitivity": SensitivityLevel.PUBLIC,
        "consent_required": False,
        "export_approved": True,
        "is_public": True,
        "publish_to_geoserver": True,
        "clip_bbox": "16.0,-35.5,33.5,-21.0",
        "country_iso3": "",
    },
    {
        "code": "WDPA_OPTIONAL",
        "title": "WDPA (optional, token-gated)",
        "description": "Optional WDPA integration source. Disabled by default and requires explicit token and URL.",
        "source_url": "https://api.protectedplanet.net/v3/protected_areas",
        "source_format": SpatialSourceFormat.OTHER,
        "source_layer_name": "",
        "license": "Protected Planet terms",
        "attribution": "UNEP-WCMC and IUCN",
        "terms_url": "https://www.protectedplanet.net/en/legal",
        "requires_token": True,
        "token_env_var": "WDPA_API_TOKEN",
        "update_frequency": UpdateFrequency.ANNUAL,
        "enabled_by_default": False,
        "source_type": SpatialLayerSourceType.EXTERNAL_WFS,
        "layer_code": "WDPA_OPTIONAL",
        "layer_title": "WDPA (optional)",
        "layer_description": "Optional restricted source: configure explicitly before use.",
        "theme": "GBF",
        "default_style_json": {"fillColor": "#6a994e", "lineColor": "#386641", "circleColor": "#386641"},
        "sensitivity": SensitivityLevel.PUBLIC,
        "consent_required": False,
        "export_approved": False,
        "is_public": False,
        "publish_to_geoserver": False,
        "clip_bbox": "",
        "country_iso3": "",
    },
]


def _download_to_temp(*, source: SpatialSource, token: str | None = None):
    url = source.source_url
    headers = {"User-Agent": "NBMS-SpatialSync/1.0"}
    if token:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        params["token"] = [token]
        query = urllib.parse.urlencode(params, doseq=True)
        url = parsed._replace(query=query).geturl()
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=120) as response:
        suggested_name = Path(urllib.parse.urlparse(url).path).name or f"{source.code}.bin"
        suffix = Path(suggested_name).suffix
        if not suffix:
            suffix_map = {
                SpatialSourceFormat.GEOJSON: ".geojson",
                SpatialSourceFormat.GPKG: ".gpkg",
                SpatialSourceFormat.SHAPEFILE: ".shp",
                SpatialSourceFormat.ZIP_SHAPEFILE: ".zip",
            }
            suffix = suffix_map.get(source.source_format, ".bin")
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                if not chunk:
                    break
                digest.update(chunk)
                handle.write(chunk)
            temp_path = Path(handle.name)

    checksum = digest.hexdigest()
    if source.expected_checksum and source.expected_checksum != checksum:
        raise RuntimeError(
            f"Checksum mismatch for {source.code}: expected {source.expected_checksum}, got {checksum}."
        )
    return temp_path, suggested_name, checksum


def ensure_default_spatial_sources(*, actor=None):
    owner = None
    if actor and getattr(actor, "is_authenticated", False):
        owner = getattr(actor, "organisation", None)
    if owner is None:
        owner = Organisation.objects.filter(org_code="SANBI").order_by("id").first()

    rows = []
    for definition in DEFAULT_SPATIAL_SOURCE_DEFINITIONS:
        defaults = {**definition, "organisation": owner}
        row, _ = SpatialSource.objects.update_or_create(code=definition["code"], defaults=defaults)
        rows.append(row)
    return rows


def _storage_key(source: SpatialSource, checksum: str, source_filename: str):
    clean_name = Path(source_filename).name or f"{source.code}.bin"
    return f"spatial/sources/{source.code.lower()}/{checksum[:12]}-{clean_name}"


def _upsert_layer_for_source(source: SpatialSource, *, user=None):
    defaults = {
        "title": source.layer_title or source.title,
        "name": source.layer_title or source.title,
        "slug": source.layer_code.lower().replace("_", "-"),
        "description": source.layer_description or source.description,
        "source_type": source.source_type,
        "data_ref": "nbms_app_spatialfeature",
        "theme": source.theme,
        "default_style_json": source.default_style_json or {},
        "attribution": source.attribution,
        "license": source.license,
        "update_frequency": source.update_frequency,
        "sensitivity": source.sensitivity,
        "consent_required": source.consent_required,
        "export_approved": source.export_approved,
        "is_public": source.is_public,
        "is_active": source.is_active,
        "publish_to_geoserver": source.publish_to_geoserver,
        "organisation": source.organisation,
        "created_by": user if getattr(user, "is_authenticated", False) else None,
        "spatial_source": source,
    }
    layer, _ = SpatialLayer.objects.update_or_create(layer_code=source.layer_code, defaults=defaults)
    return layer


def _coerce_arcgis_coord(item):
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        try:
            return [float(item[0]), float(item[1])]
        except (TypeError, ValueError):
            return None
    if isinstance(item, str):
        parts = item.replace(",", " ").split()
        if len(parts) >= 2:
            try:
                return [float(parts[0]), float(parts[1])]
            except ValueError:
                return None
    return None


def _arcgis_json_to_geojson(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    if not isinstance(features, list):
        return path

    geojson_features = []
    for feature in features:
        attrs = feature.get("attributes") or {}
        geom_src = feature.get("geometry") or {}
        geometry = None

        if "rings" in geom_src and isinstance(geom_src["rings"], list):
            rings = []
            for ring in geom_src["rings"]:
                coords = [_coerce_arcgis_coord(item) for item in (ring or [])]
                coords = [coord for coord in coords if coord]
                if len(coords) >= 4:
                    rings.append(coords)
            if rings:
                geometry = {"type": "Polygon", "coordinates": rings}
        elif "paths" in geom_src and isinstance(geom_src["paths"], list):
            paths = []
            for path_coords in geom_src["paths"]:
                coords = [_coerce_arcgis_coord(item) for item in (path_coords or [])]
                coords = [coord for coord in coords if coord]
                if len(coords) >= 2:
                    paths.append(coords)
            if paths:
                geometry = {"type": "MultiLineString", "coordinates": paths}
        elif "x" in geom_src and "y" in geom_src:
            try:
                geometry = {"type": "Point", "coordinates": [float(geom_src["x"]), float(geom_src["y"])]}
            except (TypeError, ValueError):
                geometry = None

        if geometry is None:
            continue

        feature_id = attrs.get("OBJECTID") or attrs.get("FID") or attrs.get("id")
        geojson_features.append(
            {
                "type": "Feature",
                "id": feature_id,
                "properties": attrs,
                "geometry": geometry,
            }
        )

    out_payload = {"type": "FeatureCollection", "features": geojson_features}
    out_path = path.with_suffix(".converted.geojson")
    out_path.write_text(json.dumps(out_payload), encoding="utf-8")
    return out_path


def _prepare_ingest_file(*, source: SpatialSource, file_path: Path):
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return file_path
    if not isinstance(payload, dict):
        return file_path
    if payload.get("type") == "FeatureCollection":
        return file_path
    if "features" in payload and payload["features"]:
        first = payload["features"][0]
        if isinstance(first, dict) and "attributes" in first and "geometry" in first:
            return _arcgis_json_to_geojson(file_path)
    return file_path


def sync_spatial_source(*, source: SpatialSource, actor=None, force=False, dry_run=False):
    now = timezone.now()
    result = {
        "source_code": source.code,
        "layer_code": source.layer_code,
        "status": SpatialSourceSyncStatus.READY,
        "detail": "",
        "rows_ingested": 0,
        "checksum": "",
        "storage_path": "",
        "run_id": "",
    }

    if source.requires_token:
        token = os.environ.get(source.token_env_var or "")
        if not token:
            source.last_status = SpatialSourceSyncStatus.BLOCKED
            source.last_error = f"Missing required token env var: {source.token_env_var or 'unset'}"
            source.last_sync_at = now
            source.save(update_fields=["last_status", "last_error", "last_sync_at", "updated_at"])
            result["status"] = SpatialSourceSyncStatus.BLOCKED
            result["detail"] = source.last_error
            return result

    if dry_run:
        result["status"] = SpatialSourceSyncStatus.READY
        result["detail"] = "Dry-run: source validated, ingestion not executed."
        return result

    if source.source_format == SpatialSourceFormat.OTHER:
        source.last_status = SpatialSourceSyncStatus.BLOCKED
        source.last_error = "Unsupported source format. Configure an ingestable file source (GeoJSON/GPKG/Shapefile/ZIP)."
        source.last_sync_at = now
        source.save(update_fields=["last_status", "last_error", "last_sync_at", "updated_at"])
        result["status"] = SpatialSourceSyncStatus.BLOCKED
        result["detail"] = source.last_error
        return result

    token = os.environ.get(source.token_env_var or "") if source.requires_token else None
    temp_path = None
    ingest_path = None
    try:
        temp_path, source_filename, checksum = _download_to_temp(source=source, token=token)
        ingest_path = _prepare_ingest_file(source=source, file_path=temp_path)
        ingest_filename = source_filename
        if ingest_path != temp_path:
            ingest_filename = f"{Path(source_filename).stem}.geojson"
        result["checksum"] = checksum
        if source.last_checksum == checksum and not force:
            source.last_status = SpatialSourceSyncStatus.SKIPPED
            source.last_error = ""
            source.last_sync_at = now
            source.save(update_fields=["last_status", "last_error", "last_sync_at", "updated_at"])
            result["status"] = SpatialSourceSyncStatus.SKIPPED
            result["detail"] = "Source checksum unchanged; ingestion skipped."
            return result

        storage_path = _storage_key(source, checksum, source_filename)
        if default_storage.exists(storage_path):
            default_storage.delete(storage_path)
        with temp_path.open("rb") as stream:
            default_storage.save(storage_path, File(stream, name=source_filename))
        result["storage_path"] = storage_path

        layer = _upsert_layer_for_source(source, user=actor)
        run = ingest_spatial_file(
            layer=layer,
            file_path=str(ingest_path),
            source_filename=ingest_filename,
            source_layer_name=source.source_layer_name or None,
            user=actor,
            source_storage_path=storage_path,
            source=source,
            clip_bbox=source.clip_bbox or None,
            country_iso3=source.country_iso3 or None,
        )
        result["run_id"] = run.run_id
        result["rows_ingested"] = run.rows_ingested
        if run.status != SpatialIngestionStatus.SUCCEEDED:
            source.last_status = SpatialSourceSyncStatus.FAILED
            source.last_error = (run.report_json or {}).get("error") or "Spatial ingestion failed."
            source.last_sync_at = now
            source.save(update_fields=["last_status", "last_error", "last_sync_at", "updated_at"])
            result["status"] = SpatialSourceSyncStatus.FAILED
            result["detail"] = source.last_error
            return result

        source.last_sync_at = now
        source.last_checksum = checksum
        source.last_status = SpatialSourceSyncStatus.READY
        source.last_error = ""
        source.last_feature_count = run.rows_ingested
        source.save(
            update_fields=[
                "last_sync_at",
                "last_checksum",
                "last_status",
                "last_error",
                "last_feature_count",
                "updated_at",
            ]
        )
        result["status"] = SpatialSourceSyncStatus.READY
        result["detail"] = "Ingestion succeeded."
        return result
    except Exception as exc:  # noqa: BLE001
        existing_layer = SpatialLayer.objects.filter(layer_code=source.layer_code).first()
        has_existing_data = bool(
            existing_layer and SpatialFeature.objects.filter(layer=existing_layer).values("id").exists()
        )
        if has_existing_data and source.last_checksum and not force:
            source.last_status = SpatialSourceSyncStatus.SKIPPED
            source.last_error = f"Source refresh failed; reused previous snapshot ({exc})"
            source.last_sync_at = now
            source.save(update_fields=["last_status", "last_error", "last_sync_at", "updated_at"])
            result["status"] = SpatialSourceSyncStatus.SKIPPED
            result["checksum"] = source.last_checksum
            result["detail"] = "Source refresh failed; existing layer snapshot retained."
            return result

        source.last_status = SpatialSourceSyncStatus.FAILED
        source.last_error = str(exc)
        source.last_sync_at = now
        source.save(update_fields=["last_status", "last_error", "last_sync_at", "updated_at"])
        result["status"] = SpatialSourceSyncStatus.FAILED
        result["detail"] = str(exc)
        return result
    finally:
        if temp_path:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
        if ingest_path and ingest_path != temp_path:
            try:
                ingest_path.unlink(missing_ok=True)
            except Exception:
                pass


def sync_spatial_sources(
    *,
    actor=None,
    source_codes: list[str] | None = None,
    include_optional=False,
    force=False,
    dry_run=False,
    seed_defaults=True,
):
    if seed_defaults:
        ensure_default_spatial_sources(actor=actor)

    queryset = SpatialSource.objects.filter(is_active=True).order_by("code")
    if source_codes:
        queryset = queryset.filter(code__in=source_codes)
    elif not include_optional:
        queryset = queryset.filter(enabled_by_default=True)

    results = []
    for source in queryset:
        results.append(
            sync_spatial_source(
                source=source,
                actor=actor,
                force=force,
                dry_run=dry_run,
            )
        )

    status_counts = {
        SpatialSourceSyncStatus.READY: 0,
        SpatialSourceSyncStatus.SKIPPED: 0,
        SpatialSourceSyncStatus.BLOCKED: 0,
        SpatialSourceSyncStatus.FAILED: 0,
    }
    for row in results:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    return {"results": results, "status_counts": status_counts}
