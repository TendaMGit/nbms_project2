from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from nbms_app.models import SpatialLayer, SpatialLayerSourceType
from nbms_app.services.authorization import ROLE_ADMIN, ROLE_DATA_STEWARD, ROLE_SECRETARIAT, is_system_admin, user_has_role
from nbms_app.services.audit import record_audit_event
from nbms_app.services.spatial_access import (
    etag_for_bytes,
    filter_spatial_layers_for_user,
    mvt_for_layer,
    parse_bbox,
    parse_datetime_range,
    parse_property_filters,
    spatial_feature_collection,
    tilejson_for_layer,
)
from nbms_app.services.spatial_ingest import ingest_spatial_file


def _parse_positive_int(value, default, *, minimum=0, maximum=5000):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _bbox_is_too_large(bbox, *, max_width=20.0, max_height=20.0):
    if not bbox:
        return False
    minx, miny, maxx, maxy = bbox
    return (maxx - minx) > max_width or (maxy - miny) > max_height


def _audit_actor(request):
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return user
    return None


def _layer_payload(layer):
    return {
        "uuid": str(layer.uuid),
        "layer_code": layer.layer_code,
        "name": layer.name,
        "title": layer.title or layer.name,
        "slug": layer.slug,
        "description": layer.description,
        "source_type": layer.source_type,
        "data_ref": layer.data_ref,
        "theme": layer.theme,
        "sensitivity": layer.sensitivity,
        "consent_required": layer.consent_required,
        "export_approved": layer.export_approved,
        "is_public": layer.is_public,
        "attribution": layer.attribution,
        "license": layer.license,
        "update_frequency": layer.update_frequency,
        "temporal_extent": layer.temporal_extent,
        "default_style_json": layer.default_style_json,
        "publish_to_geoserver": layer.publish_to_geoserver,
        "geoserver_layer_name": layer.geoserver_layer_name,
        "indicator": (
            {
                "uuid": str(layer.indicator.uuid),
                "code": layer.indicator.code,
                "title": layer.indicator.title,
            }
            if layer.indicator_id
            else None
        ),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def api_spatial_layers(request):
    layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.select_related("indicator"),
        request.user,
    ).order_by("theme", "title", "name", "layer_code")
    return Response({"layers": [_layer_payload(layer) for layer in layers]})


@api_view(["GET"])
@permission_classes([AllowAny])
def api_spatial_layer_features(request, slug):
    bbox = parse_bbox(request.GET.get("bbox"))
    if _bbox_is_too_large(bbox):
        return Response(
            {"detail": "bbox is too large; refine your map extent."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    province = (request.GET.get("province") or "").strip()
    indicator = (request.GET.get("indicator") or "").strip()
    year = request.GET.get("year")
    limit = _parse_positive_int(request.GET.get("limit"), 1000, minimum=1, maximum=5000)
    offset = _parse_positive_int(request.GET.get("offset"), 0, minimum=0, maximum=100000)
    parsed_year = None
    if year:
        try:
            parsed_year = int(year)
        except ValueError:
            parsed_year = None

    layer, payload = spatial_feature_collection(
        user=request.user,
        layer_slug=slug,
        bbox=bbox,
        province=province or None,
        indicator=indicator or None,
        year=parsed_year,
        limit=limit,
        offset=offset,
        datetime_range=parse_datetime_range(request.GET.get("datetime")),
        property_filters=parse_property_filters(request.GET.get("filter")),
    )
    if not layer:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_spatial_layer_export_geojson(request, layer_code):
    bbox = parse_bbox(request.GET.get("bbox"))
    if _bbox_is_too_large(bbox, max_width=30.0, max_height=30.0):
        return Response(
            {"detail": "bbox is too large for export; refine your extent."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    limit = _parse_positive_int(request.GET.get("limit"), 10000, minimum=1, maximum=20000)
    layer, payload = spatial_feature_collection(
        user=request.user,
        layer_code=layer_code,
        bbox=bbox,
        datetime_range=parse_datetime_range(request.GET.get("datetime")),
        property_filters=parse_property_filters(request.GET.get("filter")),
        limit=limit,
        offset=0,
    )
    if not layer:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    record_audit_event(
        _audit_actor(request),
        "spatial_export_geojson",
        layer,
        metadata={
            "layer_code": layer.layer_code,
            "number_returned": payload.get("numberReturned", 0),
        },
    )
    response = JsonResponse(payload, safe=True)
    response["Content-Disposition"] = f'attachment; filename="{layer.layer_code}.geojson"'
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_spatial_upload_layer(request):
    if not (
        is_system_admin(request.user)
        or getattr(request.user, "is_staff", False)
        or user_has_role(request.user, ROLE_DATA_STEWARD, ROLE_SECRETARIAT, ROLE_ADMIN)
    ):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    file_obj = request.FILES.get("file")
    layer_code = (request.data.get("layer_code") or "").strip()
    title = (request.data.get("title") or "").strip()
    source_layer_name = (request.data.get("source_layer_name") or "").strip() or None
    if not file_obj:
        return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not layer_code:
        return Response({"detail": "layer_code is required."}, status=status.HTTP_400_BAD_REQUEST)

    layer, _created = SpatialLayer.objects.update_or_create(
        layer_code=layer_code,
        defaults={
            "title": title or layer_code,
            "name": title or layer_code,
            "slug": layer_code.lower().replace("_", "-"),
            "source_type": SpatialLayerSourceType.UPLOADED_FILE,
            "is_public": False,
            "is_active": True,
            "created_by": request.user,
            "organisation": getattr(request.user, "organisation", None),
        },
    )

    suffix = Path(file_obj.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        for chunk in file_obj.chunks():
            handle.write(chunk)
        temp_path = Path(handle.name)

    storage_key = f"spatial/uploads/{uuid.uuid4()}-{file_obj.name}"
    with temp_path.open("rb") as stream:
        default_storage.save(storage_key, File(stream, name=file_obj.name))
    layer.source_file.name = storage_key
    layer.save(update_fields=["source_file", "updated_at"])

    try:
        run = ingest_spatial_file(
            layer=layer,
            file_path=str(temp_path),
            source_filename=file_obj.name,
            source_layer_name=source_layer_name,
            user=request.user,
            source_storage_path=storage_key,
        )
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    if run.status != "succeeded":
        return Response(
            {
                "detail": "Spatial ingestion failed.",
                "run_id": run.run_id,
                "report_json": run.report_json,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "detail": "Spatial layer ingested.",
            "layer": _layer_payload(layer),
            "run_id": run.run_id,
            "rows_ingested": run.rows_ingested,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_ogc_landing(request):
    base = request.build_absolute_uri("/api/ogc")
    return Response(
        {
            "title": "NBMS OGC API",
            "description": "NBMS OGC API - Features compatible landing page.",
            "links": [
                {"rel": "self", "type": "application/json", "href": base},
                {"rel": "data", "type": "application/json", "href": request.build_absolute_uri("/api/ogc/collections")},
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_ogc_collections(request):
    layers = filter_spatial_layers_for_user(SpatialLayer.objects.select_related("indicator"), request.user).order_by(
        "theme", "title", "name", "layer_code"
    )
    return Response(
        {
            "collections": [
                {
                    "id": layer.layer_code,
                    "title": layer.title or layer.name,
                    "description": layer.description,
                    "itemType": "feature",
                    "extent": {"temporal": layer.temporal_extent or {}},
                    "links": [
                        {
                            "rel": "items",
                            "type": "application/geo+json",
                            "href": request.build_absolute_uri(f"/api/ogc/collections/{layer.layer_code}/items"),
                        }
                    ],
                }
                for layer in layers
            ]
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def api_ogc_collection_items(request, layer_code):
    limit = _parse_positive_int(request.GET.get("limit"), 1000, minimum=1, maximum=5000)
    offset = _parse_positive_int(request.GET.get("offset"), 0, minimum=0, maximum=100000)
    bbox = parse_bbox(request.GET.get("bbox"))
    if _bbox_is_too_large(bbox):
        return Response(
            {"detail": "bbox is too large; refine your map extent."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    layer, payload = spatial_feature_collection(
        user=request.user,
        layer_code=layer_code,
        bbox=bbox,
        datetime_range=parse_datetime_range(request.GET.get("datetime")),
        property_filters=parse_property_filters(request.GET.get("filter")),
        limit=limit,
        offset=offset,
    )
    if not layer:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    payload["links"] = [
        {
            "rel": "self",
            "type": "application/geo+json",
            "href": request.build_absolute_uri(),
        }
    ]
    record_audit_event(
        _audit_actor(request),
        "spatial_ogc_items",
        layer,
        metadata={
            "layer_code": layer.layer_code,
            "number_returned": payload.get("numberReturned", 0),
            "offset": offset,
            "limit": limit,
        },
    )
    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def api_tiles_tilejson(request, layer_code):
    layer = get_object_or_404(filter_spatial_layers_for_user(SpatialLayer.objects.all(), request.user), layer_code=layer_code)
    return Response(tilejson_for_layer(layer=layer, request=request))


@api_view(["GET"])
@permission_classes([AllowAny])
def api_tiles_mvt(request, layer_code, z, x, y):
    layer = get_object_or_404(filter_spatial_layers_for_user(SpatialLayer.objects.all(), request.user), layer_code=layer_code)
    payload = mvt_for_layer(
        layer=layer,
        user=request.user,
        z=int(z),
        x=int(x),
        y=int(y),
        property_filters=parse_property_filters(request.GET.get("filter")),
        datetime_range=parse_datetime_range(request.GET.get("datetime")),
        max_features=_parse_positive_int(request.GET.get("limit"), 5000, minimum=100, maximum=10000),
    )
    if payload is None:
        payload = b""
    etag = etag_for_bytes(payload)
    if request.headers.get("If-None-Match") == f'"{etag}"':
        return HttpResponse(status=status.HTTP_304_NOT_MODIFIED)
    response = HttpResponse(payload, content_type="application/vnd.mapbox-vector-tile")
    response["ETag"] = f'"{etag}"'
    response["Cache-Control"] = "public, max-age=300"
    return response
