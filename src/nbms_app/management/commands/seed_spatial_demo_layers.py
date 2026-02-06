from django.core.management.base import BaseCommand

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
)


def _polygon(coords):
    return {"type": "Polygon", "coordinates": [coords]}


PROVINCE_FEATURES = [
    {
        "key": "ZA-WC",
        "name": "Western Cape",
        "province_code": "WC",
        "geometry": _polygon([[17.0, -35.5], [21.5, -35.5], [21.5, -32.0], [17.0, -32.0], [17.0, -35.5]]),
    },
    {
        "key": "ZA-EC",
        "name": "Eastern Cape",
        "province_code": "EC",
        "geometry": _polygon([[21.5, -34.8], [29.5, -34.8], [29.5, -30.2], [21.5, -30.2], [21.5, -34.8]]),
    },
    {
        "key": "ZA-KZN",
        "name": "KwaZulu-Natal",
        "province_code": "KZN",
        "geometry": _polygon([[29.0, -31.8], [33.2, -31.8], [33.2, -26.8], [29.0, -26.8], [29.0, -31.8]]),
    },
]

PROTECTED_AREA_FEATURES = [
    {
        "key": "PA-001",
        "name": "Kruger National Park",
        "province_code": "MP",
        "geometry": _polygon([[31.0, -25.5], [32.0, -25.5], [32.0, -22.2], [31.0, -22.2], [31.0, -25.5]]),
        "properties": {"designation": "National Park", "iucn_category": "II"},
    },
    {
        "key": "PA-002",
        "name": "Table Mountain National Park",
        "province_code": "WC",
        "geometry": _polygon([[18.3, -34.4], [18.6, -34.4], [18.6, -33.9], [18.3, -33.9], [18.3, -34.4]]),
        "properties": {"designation": "National Park", "iucn_category": "II"},
    },
]

INDICATOR_LAYER_FEATURES = [
    {
        "key": "THREAT-2022-WC",
        "name": "Threatened ecosystem hotspot (WC)",
        "province_code": "WC",
        "year": 2022,
        "geometry": _polygon([[18.0, -34.2], [19.2, -34.2], [19.2, -33.1], [18.0, -33.1], [18.0, -34.2]]),
        "properties": {"threat_status": "endangered", "confidence": "medium"},
    },
    {
        "key": "THREAT-2022-EC",
        "name": "Threatened ecosystem hotspot (EC)",
        "province_code": "EC",
        "year": 2022,
        "geometry": _polygon([[25.2, -33.4], [26.6, -33.4], [26.6, -32.3], [25.2, -32.3], [25.2, -33.4]]),
        "properties": {"threat_status": "critical", "confidence": "high"},
    },
]


class Command(BaseCommand):
    help = "Seed demo spatial layers and features (idempotent)."

    def handle(self, *args, **options):
        provinces_layer, _ = SpatialLayer.objects.update_or_create(
            slug="sa-provinces",
            defaults={
                "name": "South Africa Provinces (demo)",
                "description": "Simplified province polygons for demo map workflows.",
                "source_type": SpatialLayerSourceType.STATIC,
                "sensitivity": SensitivityLevel.PUBLIC,
                "is_public": True,
                "is_active": True,
                "default_style_json": {"fillColor": "#7ca982", "lineColor": "#2f5d50"},
            },
        )
        protected_layer, _ = SpatialLayer.objects.update_or_create(
            slug="protected-areas-demo",
            defaults={
                "name": "Protected Areas (demo)",
                "description": "Simplified protected area polygons for dashboard/map demos.",
                "source_type": SpatialLayerSourceType.STATIC,
                "sensitivity": SensitivityLevel.PUBLIC,
                "is_public": True,
                "is_active": True,
                "default_style_json": {"fillColor": "#4d9078", "lineColor": "#1b4332"},
            },
        )

        indicator = (
            Indicator.objects.filter(code__in=["NBMS-GBF-PA-COVERAGE", "NBMS-GBF-ECOSYSTEM-THREAT"])
            .order_by("code")
            .first()
        )
        indicator_layer, _ = SpatialLayer.objects.update_or_create(
            slug="ecosystem-threat-status-demo",
            defaults={
                "name": "Ecosystem Threat Status (demo)",
                "description": "Indicator-linked threat status polygons for map integration.",
                "source_type": SpatialLayerSourceType.INDICATOR,
                "sensitivity": SensitivityLevel.PUBLIC,
                "is_public": True,
                "is_active": True,
                "indicator": indicator,
                "default_style_json": {"fillColor": "#ff9f1c", "lineColor": "#9d0208"},
            },
        )

        created = 0
        for item in PROVINCE_FEATURES:
            _, was_created = SpatialFeature.objects.update_or_create(
                layer=provinces_layer,
                feature_key=item["key"],
                defaults={
                    "name": item["name"],
                    "province_code": item["province_code"],
                    "geometry_json": item["geometry"],
                    "properties_json": {
                        "layer_type": "province",
                        "status": LifecycleStatus.PUBLISHED,
                    },
                },
            )
            created += int(was_created)

        for item in PROTECTED_AREA_FEATURES:
            _, was_created = SpatialFeature.objects.update_or_create(
                layer=protected_layer,
                feature_key=item["key"],
                defaults={
                    "name": item["name"],
                    "province_code": item["province_code"],
                    "geometry_json": item["geometry"],
                    "properties_json": item["properties"],
                },
            )
            created += int(was_created)

        for item in INDICATOR_LAYER_FEATURES:
            _, was_created = SpatialFeature.objects.update_or_create(
                layer=indicator_layer,
                feature_key=item["key"],
                defaults={
                    "name": item["name"],
                    "province_code": item["province_code"],
                    "year": item["year"],
                    "indicator": indicator,
                    "geometry_json": item["geometry"],
                    "properties_json": item["properties"],
                },
            )
            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Spatial demo layers ready. Layers={SpatialLayer.objects.count()}, "
                f"features={SpatialFeature.objects.count()}, created={created}."
            )
        )
