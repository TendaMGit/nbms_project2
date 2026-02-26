from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from django.contrib.contenttypes.models import ContentType
from django.db import ProgrammingError, connection
from django.db.models import Q

from nbms_app.models import (
    ConsentRecord,
    ConsentStatus,
    Indicator,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
)
from nbms_app.services.authorization import (
    ROLE_COMMUNITY_REPRESENTATIVE,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)
from nbms_app.spatial_fields import GIS_ENABLED

try:  # pragma: no cover - exercised in GIS runtime
    from django.contrib.gis.geos import GEOSGeometry, Polygon
except Exception:  # pragma: no cover - exercised in non-GIS runtime
    GEOSGeometry = None
    Polygon = None


def _consent_q(layer_qs):
    content_type = ContentType.objects.get_for_model(SpatialLayer)
    granted = ConsentRecord.objects.filter(
        content_type=content_type,
        status=ConsentStatus.GRANTED,
        reporting_instance__isnull=True,
    ).values_list("object_uuid", flat=True)
    return layer_qs.filter(Q(consent_required=False) | Q(uuid__in=granted))


def filter_spatial_layers_for_user(queryset, user, *, include_inactive=False):
    qs = queryset
    if not include_inactive:
        qs = qs.filter(is_active=True)
    qs = _consent_q(qs)
    if is_system_admin(user):
        return qs
    if not user or not getattr(user, "is_authenticated", False):
        return qs.filter(is_public=True, sensitivity=SensitivityLevel.PUBLIC)

    org_id = getattr(user, "organisation_id", None)
    org_q = Q(pk__in=[])
    if org_id:
        org_q = Q(organisation_id=org_id)

    public_q = Q(is_public=True, sensitivity=SensitivityLevel.PUBLIC)
    creator_q = Q(created_by_id=getattr(user, "id", None))
    internal_q = Q(
        is_public=True,
        sensitivity__in=[SensitivityLevel.INTERNAL, SensitivityLevel.RESTRICTED],
    ) & org_q
    community_q = Q(is_public=True, sensitivity=SensitivityLevel.IPLC_SENSITIVE) & org_q
    if not user_has_role(user, ROLE_COMMUNITY_REPRESENTATIVE):
        community_q = Q(pk__in=[])

    return qs.filter(public_q | creator_q | internal_q | community_q).distinct()


def filter_spatial_features_for_user(queryset, user):
    visible_layers = filter_spatial_layers_for_user(SpatialLayer.objects.all(), user)
    qs = queryset.filter(layer__in=visible_layers)

    visible_indicators = filter_queryset_for_user(
        Indicator.objects.all(),
        user,
        perm="nbms_app.view_indicator",
    ).values_list("id", flat=True)
    return qs.filter(Q(indicator__isnull=True) | Q(indicator_id__in=visible_indicators))


def parse_bbox(value):
    if not value:
        return None
    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 4:
        return None
    try:
        minx, miny, maxx, maxy = tuple(float(item) for item in parts)
    except ValueError:
        return None
    if minx >= maxx or miny >= maxy:
        return None
    return minx, miny, maxx, maxy


def parse_datetime_range(value):
    if not value:
        return None
    if "/" not in value:
        return None
    start_raw, end_raw = value.split("/", 1)
    start_raw = start_raw.strip()
    end_raw = end_raw.strip()

    def _coerce(raw):
        if not raw or raw == "..":
            return None
        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            try:
                return date.fromisoformat(raw)
            except ValueError:
                return None

    start = _coerce(start_raw)
    end = _coerce(end_raw)
    if not start and not end:
        return None
    return start, end


def parse_property_filters(value):
    if not value:
        return {}
    result = {}
    for chunk in value.split(","):
        if "=" not in chunk:
            continue
        key, raw_value = chunk.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            continue
        result[key] = raw_value
    return result


def _round_coords(node, precision):
    if isinstance(node, list):
        if len(node) >= 2 and isinstance(node[0], (int, float)) and isinstance(node[1], (int, float)):
            return [round(float(node[0]), precision), round(float(node[1]), precision), *node[2:]]
        return [_round_coords(item, precision) for item in node]
    return node


def _generalize_geometry(layer, user, geometry):
    if not isinstance(geometry, dict):
        return geometry
    if is_system_admin(user):
        return geometry
    if layer.sensitivity in {SensitivityLevel.RESTRICTED, SensitivityLevel.IPLC_SENSITIVE}:
        coords = geometry.get("coordinates")
        return {**geometry, "coordinates": _round_coords(coords, 3)}
    return geometry


def _geometry_to_json(feature):
    if feature.geometry_json:
        return feature.geometry_json
    if feature.geom and hasattr(feature.geom, "geojson"):
        try:
            return json.loads(feature.geom.geojson)
        except Exception:
            return None
    return None


def _apply_bbox(qs, bbox):
    if not bbox:
        return qs
    minx, miny, maxx, maxy = bbox
    if GIS_ENABLED and Polygon:
        try:
            poly = Polygon.from_bbox((minx, miny, maxx, maxy))
            poly.srid = 4326
            return qs.filter(
                Q(geom__intersects=poly)
                | (
                    Q(geom__isnull=True)
                    & Q(minx__lte=maxx)
                    & Q(maxx__gte=minx)
                    & Q(miny__lte=maxy)
                    & Q(maxy__gte=miny)
                )
            )
        except Exception:
            pass
    return qs.filter(
        minx__lte=maxx,
        maxx__gte=minx,
        miny__lte=maxy,
        maxy__gte=miny,
    )


def _apply_datetime(qs, datetime_range):
    if not datetime_range:
        return qs
    start, end = datetime_range
    if start:
        qs = qs.filter(Q(valid_to__isnull=True) | Q(valid_to__gte=start))
    if end:
        qs = qs.filter(Q(valid_from__isnull=True) | Q(valid_from__lte=end))
    return qs


def _apply_property_filters(qs, property_filters):
    for key, value in (property_filters or {}).items():
        qs = qs.filter(properties__contains={key: value})
    return qs


def _collection_payload(layer, rows, *, user, total, limit, offset):
    features = []
    for feature in rows:
        props = dict(feature.properties or feature.properties_json or {})
        props.update(
            {
                "feature_id": feature.feature_id or feature.feature_key,
                "feature_key": feature.feature_key,
                "name": feature.name,
                "province_code": feature.province_code,
                "year": feature.year,
                "layer_code": layer.layer_code,
                "layer_slug": layer.slug,
            }
        )
        if feature.indicator_id:
            props["indicator"] = {
                "uuid": str(feature.indicator.uuid),
                "code": feature.indicator.code,
                "title": feature.indicator.title,
            }
        geometry = _generalize_geometry(layer, user, _geometry_to_json(feature))
        features.append(
            {
                "type": "Feature",
                "id": str(feature.uuid),
                "geometry": geometry,
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "numberMatched": total,
        "numberReturned": len(features),
        "limit": limit,
        "offset": offset,
        "features": features,
    }


def spatial_feature_collection(
    *,
    user,
    layer_code=None,
    layer_slug=None,
    bbox=None,
    province=None,
    indicator=None,
    year=None,
    datetime_range=None,
    property_filters=None,
    limit=1000,
    offset=0,
):
    layers = filter_spatial_layers_for_user(SpatialLayer.objects.select_related("indicator"), user)
    layer = None
    if layer_code:
        layer = layers.filter(layer_code=layer_code).first()
    if not layer and layer_slug:
        layer = layers.filter(slug=layer_slug).first()
    if not layer:
        return None, {
            "type": "FeatureCollection",
            "numberMatched": 0,
            "numberReturned": 0,
            "features": [],
        }

    qs = filter_spatial_features_for_user(
        SpatialFeature.objects.select_related("indicator", "layer"),
        user,
    ).filter(layer=layer)

    if province:
        qs = qs.filter(province_code__iexact=province.strip())
    if year:
        qs = qs.filter(Q(year=year) | Q(year__isnull=True))
    if indicator:
        qs = qs.filter(Q(indicator__uuid=indicator) | Q(indicator__code__iexact=indicator))

    qs = _apply_bbox(qs, bbox)
    qs = _apply_datetime(qs, datetime_range)
    qs = _apply_property_filters(qs, property_filters)

    qs = qs.order_by("feature_key", "id")
    total = qs.count()
    rows = list(qs[offset : offset + max(1, min(limit, 5000))])
    return layer, _collection_payload(layer, rows, user=user, total=total, limit=limit, offset=offset)


def tilejson_for_layer(*, layer, request, minzoom=0, maxzoom=12):
    tile_url = request.build_absolute_uri(f"/api/tiles/{layer.layer_code}/{{z}}/{{x}}/{{y}}.pbf")
    return {
        "tilejson": "3.0.0",
        "name": layer.title or layer.name,
        "description": layer.description,
        "attribution": layer.attribution or "",
        "tiles": [tile_url],
        "minzoom": minzoom,
        "maxzoom": maxzoom,
        "vector_layers": [{"id": layer.layer_code.lower(), "fields": {}}],
    }


def mvt_for_layer(
    *,
    layer,
    user,
    z,
    x,
    y,
    property_filters=None,
    datetime_range=None,
    max_features=5000,
):
    # Defensive hard limits
    if z < 0 or z > 14:
        return b""
    if not GIS_ENABLED:
        return b""

    visible = filter_spatial_layers_for_user(SpatialLayer.objects.filter(id=layer.id), user)
    if not visible.exists():
        return b""

    geom_sql = (
        "CASE "
        "WHEN geom IS NOT NULL THEN geom "
        "WHEN geometry_json ? 'type' THEN ST_SetSRID(ST_GeomFromGeoJSON(geometry_json::text), 4326) "
        "ELSE NULL "
        "END"
    )
    where_sql = ["layer_id = %s", f"{geom_sql} IS NOT NULL"]
    params = [layer.id]

    for key, value in (property_filters or {}).items():
        where_sql.append("(COALESCE(properties, properties_json) ->> %s) = %s")
        params.extend([key, value])

    if datetime_range:
        start, end = datetime_range
        if start:
            where_sql.append("(valid_to IS NULL OR valid_to >= %s)")
            params.append(start)
        if end:
            where_sql.append("(valid_from IS NULL OR valid_from <= %s)")
            params.append(end)

    where_clause = " AND ".join(where_sql)
    sql = f"""
        WITH bounds AS (
            SELECT ST_TileEnvelope(%s, %s, %s) AS geom
        ),
        source AS (
            SELECT
                id,
                feature_id,
                feature_key,
                name,
                province_code,
                year,
                COALESCE(properties, properties_json) AS props,
                ST_AsMVTGeom(
                    ST_Transform(
                        {geom_sql},
                        3857
                    ),
                    bounds.geom,
                    4096,
                    64,
                    true
                ) AS geom
            FROM nbms_app_spatialfeature, bounds
            WHERE {where_clause}
              AND ST_Intersects(
                  ST_Transform({geom_sql}, 3857),
                  bounds.geom
              )
            ORDER BY feature_key, id
            LIMIT %s
        )
        SELECT ST_AsMVT(source, %s, 4096, 'geom') FROM source
    """
    params = [z, x, y, *params, max(1, min(max_features, 10000)), layer.layer_code.lower()]
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
    except ProgrammingError:
        # Spatial SQL functions (PostGIS) are unavailable in this runtime.
        return b""
    return row[0] if row and row[0] else b""


def etag_for_bytes(payload):
    return hashlib.sha256(payload).hexdigest()
