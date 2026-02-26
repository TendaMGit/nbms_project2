from __future__ import annotations

import os

from django.db import models

GIS_ENABLED = False

def _gis_requested() -> bool:
    raw = os.environ.get("ENABLE_GIS")
    if raw is not None:
        return raw.lower() == "true"
    try:
        from django.conf import settings

        return bool(getattr(settings, "ENABLE_GIS", False))
    except Exception:
        return False


if _gis_requested():
    try:
        from django.contrib.gis.db import models as gis_models
        from django.contrib.postgres.indexes import GistIndex as _GistIndex

        GeometryField = gis_models.GeometryField
        MultiPolygonField = gis_models.MultiPolygonField
        PointField = gis_models.PointField
        PolygonField = gis_models.PolygonField
        GistIndex = _GistIndex
        GIS_ENABLED = True
    except Exception:
        GIS_ENABLED = False

if not GIS_ENABLED:  # pragma: no cover - exercised in non-GIS environments
    class _FallbackGeometryField(models.JSONField):
        def __init__(self, *args, **kwargs):
            kwargs.pop("srid", None)
            kwargs.pop("geography", None)
            kwargs.pop("spatial_index", None)
            kwargs.setdefault("blank", True)
            kwargs.setdefault("null", True)
            kwargs.setdefault("default", dict)
            super().__init__(*args, **kwargs)

    class _FallbackGistIndex(models.Index):
        pass

    GeometryField = _FallbackGeometryField
    MultiPolygonField = _FallbackGeometryField
    PointField = _FallbackGeometryField
    PolygonField = _FallbackGeometryField
    GistIndex = _FallbackGistIndex
