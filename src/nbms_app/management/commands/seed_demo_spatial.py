from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db.models import Q

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    MonitoringProgramme,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
    SpatialUnit,
    SpatialUnitType,
)
from nbms_app.spatial_fields import GIS_ENABLED

try:  # pragma: no cover - exercised in GIS runtime
    from django.contrib.gis.geos import GEOSGeometry
except Exception:  # pragma: no cover - exercised in non-GIS runtime
    GEOSGeometry = None


def _polygon(coords):
    return {"type": "Polygon", "coordinates": [coords]}


def _geometry(value):
    if GIS_ENABLED and GEOSGeometry:
        try:
            return GEOSGeometry(json.dumps(value), srid=4326)
        except Exception:
            return None
    return value


def _as_multipolygon(value):
    if not isinstance(value, dict):
        return value
    if value.get("type") == "MultiPolygon":
        return value
    if value.get("type") == "Polygon" and isinstance(value.get("coordinates"), list):
        return {"type": "MultiPolygon", "coordinates": [value["coordinates"]]}
    return value


def _upsert_layer(*, layer_code, defaults):
    layer = SpatialLayer.objects.filter(Q(layer_code=layer_code) | Q(slug=defaults.get("slug", ""))).order_by("id").first()
    if layer:
        for key, value in defaults.items():
            setattr(layer, key, value)
        layer.layer_code = layer_code
        layer.save()
        return layer, False
    return SpatialLayer.objects.create(layer_code=layer_code, **defaults), True


PROVINCES = [
    {
        "code": "ZA-WC",
        "name": "Western Cape",
        "province_code": "WC",
        "geometry": _polygon([[17.0, -35.5], [21.5, -35.5], [21.5, -32.0], [17.0, -32.0], [17.0, -35.5]]),
    },
    {
        "code": "ZA-EC",
        "name": "Eastern Cape",
        "province_code": "EC",
        "geometry": _polygon([[21.5, -34.8], [29.5, -34.8], [29.5, -30.2], [21.5, -30.2], [21.5, -34.8]]),
    },
    {
        "code": "ZA-KZN",
        "name": "KwaZulu-Natal",
        "province_code": "KZN",
        "geometry": _polygon([[29.0, -31.8], [33.2, -31.8], [33.2, -26.8], [29.0, -26.8], [29.0, -31.8]]),
    },
]

PROTECTED_AREAS = [
    {
        "feature_id": "PA-001",
        "name": "Kruger National Park",
        "province_code": "MP",
        "geometry": _polygon([[31.0, -25.5], [32.0, -25.5], [32.0, -22.2], [31.0, -22.2], [31.0, -25.5]]),
        "properties": {"designation": "National Park", "iucn_category": "II"},
    },
    {
        "feature_id": "PA-002",
        "name": "Table Mountain National Park",
        "province_code": "WC",
        "geometry": _polygon([[18.3, -34.4], [18.6, -34.4], [18.6, -33.9], [18.3, -33.9], [18.3, -34.4]]),
        "properties": {"designation": "National Park", "iucn_category": "II"},
    },
]

THREAT_LAYER = [
    {
        "feature_id": "THREAT-2022-WC",
        "name": "Threatened ecosystem hotspot (WC)",
        "province_code": "WC",
        "year": 2022,
        "geometry": _polygon([[18.0, -34.2], [19.2, -34.2], [19.2, -33.1], [18.0, -33.1], [18.0, -34.2]]),
        "properties": {"threat_status": "endangered", "confidence": "medium", "area_ha": 25340.1},
    },
    {
        "feature_id": "THREAT-2022-EC",
        "name": "Threatened ecosystem hotspot (EC)",
        "province_code": "EC",
        "year": 2022,
        "geometry": _polygon([[25.2, -33.4], [26.6, -33.4], [26.6, -32.3], [25.2, -32.3], [25.2, -33.4]]),
        "properties": {"threat_status": "critical", "confidence": "high", "area_ha": 33490.9},
    },
]


class Command(BaseCommand):
    help = "Seed full demo spatial registry data (idempotent)."

    def handle(self, *args, **options):
        province_type, _ = SpatialUnitType.objects.update_or_create(
            code="PROVINCE",
            defaults={
                "name": "Province",
                "description": "South African provinces (demo subset).",
                "default_geom_type": "polygon",
                "admin_level": 1,
                "is_active": True,
            },
        )

        province_units = {}
        for item in PROVINCES:
            unit, _ = SpatialUnit.objects.update_or_create(
                unit_code=item["code"],
                defaults={
                "name": item["name"],
                "unit_type": province_type,
                "geom": _geometry(_as_multipolygon(item["geometry"])),
                "properties": {"province_code": item["province_code"]},
                "sensitivity": SensitivityLevel.PUBLIC,
                    "consent_required": False,
                    "is_active": True,
                },
            )
            province_units[item["province_code"]] = unit

        provinces_layer, _ = _upsert_layer(
            layer_code="ZA_PROVINCES",
            defaults={
                "title": "South Africa Provinces",
                "name": "South Africa Provinces",
                "slug": "sa-provinces",
                "description": "Administrative provinces used for indicator disaggregation.",
                "theme": "Admin",
                "source_type": SpatialLayerSourceType.NBMS_TABLE,
                "data_ref": "nbms_app_spatialunit",
                "sensitivity": SensitivityLevel.PUBLIC,
                "consent_required": False,
                "export_approved": True,
                "is_public": True,
                "is_active": True,
                "default_style_json": {"fillColor": "#7ca982", "lineColor": "#2f5d50"},
                "attribution": "NBMS demo",
                "license": "CC-BY-4.0",
            },
        )
        protected_layer, _ = _upsert_layer(
            layer_code="ZA_PROTECTED_AREAS",
            defaults={
                "title": "Protected Areas",
                "name": "Protected Areas",
                "slug": "protected-areas-demo",
                "description": "Protected area polygons for reporting maps.",
                "theme": "GBF",
                "source_type": SpatialLayerSourceType.NBMS_TABLE,
                "data_ref": "nbms_app_spatialfeature",
                "sensitivity": SensitivityLevel.PUBLIC,
                "consent_required": False,
                "export_approved": True,
                "is_public": True,
                "is_active": True,
                "default_style_json": {"fillColor": "#4d9078", "lineColor": "#1b4332"},
                "attribution": "NBMS demo",
                "license": "CC-BY-4.0",
            },
        )

        indicator = (
            Indicator.objects.filter(code__in=["NBMS-GBF-ECOSYSTEM-THREAT", "NBMS-GBF-PA-COVERAGE"]).order_by("code").first()
        )
        threat_layer, _ = _upsert_layer(
            layer_code="ZA_ECOSYSTEM_THREAT_STATUS",
            defaults={
                "title": "Ecosystem Threat Status",
                "name": "Ecosystem Threat Status",
                "slug": "ecosystem-threat-status-demo",
                "description": "Threat status polygons linked to indicator reporting.",
                "theme": "GBF",
                "source_type": SpatialLayerSourceType.NBMS_TABLE,
                "data_ref": "nbms_app_spatialfeature",
                "sensitivity": SensitivityLevel.PUBLIC,
                "consent_required": False,
                "export_approved": True,
                "is_public": True,
                "is_active": True,
                "indicator": indicator,
                "default_style_json": {"fillColor": "#ff9f1c", "lineColor": "#9d0208"},
                "attribution": "NBMS demo",
                "license": "CC-BY-4.0",
            },
        )

        created = 0
        for item in PROVINCES:
            unit = province_units.get(item["province_code"])
            _, was_created = SpatialFeature.objects.update_or_create(
                layer=provinces_layer,
                feature_key=item["code"],
                defaults={
                    "feature_id": item["code"],
                    "name": item["name"],
                    "province_code": item["province_code"],
                    "spatial_unit": unit,
                    "geom": _geometry(item["geometry"]),
                    "geometry_json": item["geometry"],
                    "properties": {"layer_type": "province", "status": LifecycleStatus.PUBLISHED},
                    "properties_json": {"layer_type": "province", "status": LifecycleStatus.PUBLISHED},
                },
            )
            created += int(was_created)

        for item in PROTECTED_AREAS:
            _, was_created = SpatialFeature.objects.update_or_create(
                layer=protected_layer,
                feature_key=item["feature_id"],
                defaults={
                    "feature_id": item["feature_id"],
                    "name": item["name"],
                    "province_code": item["province_code"],
                    "geom": _geometry(item["geometry"]),
                    "geometry_json": item["geometry"],
                    "properties": item["properties"],
                    "properties_json": item["properties"],
                },
            )
            created += int(was_created)

        for item in THREAT_LAYER:
            unit = province_units.get(item["province_code"])
            _, was_created = SpatialFeature.objects.update_or_create(
                layer=threat_layer,
                feature_key=item["feature_id"],
                defaults={
                    "feature_id": item["feature_id"],
                    "name": item["name"],
                    "province_code": item["province_code"],
                    "year": item["year"],
                    "indicator": indicator,
                    "spatial_unit": unit,
                    "geom": _geometry(item["geometry"]),
                    "geometry_json": item["geometry"],
                    "properties": item["properties"],
                    "properties_json": item["properties"],
                },
            )
            created += int(was_created)

        programme = MonitoringProgramme.objects.filter(programme_code="NBMS-MONITORING-CORE").first()
        if programme:
            programme.coverage_units.set(SpatialUnit.objects.filter(unit_type=province_type, is_active=True))

        self.stdout.write(
            self.style.SUCCESS(
                f"Spatial demo ready. unit_types={SpatialUnitType.objects.count()}, units={SpatialUnit.objects.count()}, "
                f"layers={SpatialLayer.objects.count()}, features={SpatialFeature.objects.count()}, created={created}."
            )
        )
