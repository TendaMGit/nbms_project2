from django.db.models import Q

from nbms_app.models import (
    Indicator,
    LifecycleStatus,
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


def filter_spatial_layers_for_user(queryset, user):
    qs = queryset.filter(is_active=True)
    if is_system_admin(user):
        return qs
    if not user or not getattr(user, "is_authenticated", False):
        return qs.filter(is_public=True, sensitivity=SensitivityLevel.PUBLIC)

    org_id = getattr(user, "organisation_id", None)
    org_q = Q()
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


def spatial_feature_collection(
    *,
    user,
    layer_slug,
    bbox=None,
    province=None,
    indicator=None,
    year=None,
    limit=1000,
):
    layers = filter_spatial_layers_for_user(SpatialLayer.objects.select_related("indicator"), user)
    layer = layers.filter(slug=layer_slug).first()
    if not layer:
        return None, {"type": "FeatureCollection", "features": []}

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

    if bbox:
        minx, miny, maxx, maxy = bbox
        qs = qs.filter(
            minx__lte=maxx,
            maxx__gte=minx,
            miny__lte=maxy,
            maxy__gte=miny,
        )

    qs = qs.order_by("feature_key", "id")[: max(1, min(limit, 5000))]

    features = []
    for feature in qs:
        properties = dict(feature.properties_json or {})
        properties.update(
            {
                "feature_key": feature.feature_key,
                "name": feature.name,
                "province_code": feature.province_code,
                "year": feature.year,
                "layer_slug": layer.slug,
            }
        )
        if feature.indicator_id:
            properties["indicator"] = {
                "uuid": str(feature.indicator.uuid),
                "code": feature.indicator.code,
                "title": feature.indicator.title,
            }
        features.append(
            {
                "type": "Feature",
                "id": str(feature.uuid),
                "geometry": feature.geometry_json,
                "properties": properties,
            }
        )

    return layer, {"type": "FeatureCollection", "features": features}


def parse_bbox(value):
    if not value:
        return None
    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 4:
        return None
    try:
        return tuple(float(item) for item in parts)
    except ValueError:
        return None
