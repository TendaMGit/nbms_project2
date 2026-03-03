from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Q

from nbms_app.models import (
    AuditEvent,
    DatasetRelease,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorMethodologyVersionLink,
    IndicatorValueType,
    LifecycleStatus,
    ReportingCycle,
    SpatialLayer,
)
from nbms_app.services.indicator_data import indicator_data_points_for_user, indicator_data_series_for_user
from nbms_app.services.indicator_packs import (
    build_pack_dimensions,
    build_pack_profile,
    list_pack_dimensions,
    resolve_indicator_pack,
)
from nbms_app.services.spatial_access import filter_spatial_layers_for_user, spatial_feature_collection


_TAXONOMY_DIMENSIONS = {
    "taxonomy_kingdom": ["taxonomy_kingdom", "kingdom"],
    "taxonomy_phylum": ["taxonomy_phylum", "phylum"],
    "taxonomy_class": ["taxonomy_class", "class_name", "class"],
    "taxonomy_order": ["taxonomy_order", "order"],
    "taxonomy_family": ["taxonomy_family", "family"],
    "taxonomy_genus": ["taxonomy_genus", "genus"],
    "taxonomy_species": ["taxonomy_species", "species", "scientific_name"],
}

_GEO_DIMENSIONS = {
    "province": [("province_code", "province_name"), ("province", "province_name")],
    "municipality": [("municipality_code", "municipality_name"), ("municipality", "municipality_name")],
    "biome": [("biome_code", "biome_name"), ("biome", "biome_name")],
    "ecoregion": [("ecoregion_code", "ecoregion_name"), ("ecoregion", "ecoregion_name")],
    "realm": [("realm_code", "realm_name"), ("realm", "realm_name")],
}

_CATEGORY_DIMENSIONS = {
    "threat_category": [("threat_category", "threat_category_label"), ("category", "category_label")],
    "protection_category": [("protection_category", "protection_category_label")],
    "category": [("category", "category_label"), ("status", "status_label")],
}

_DIMENSION_LABELS = {
    "year": "Year",
    "release": "Dataset release",
    "value_text": "Category",
    "province": "Province",
    "municipality": "Municipality",
    "biome": "Biome",
    "ecoregion": "Ecoregion",
    "realm": "Realm",
    "threat_category": "Threat category",
    "protection_category": "Protection category",
    "category": "Category",
    "taxonomy_kingdom": "Kingdom",
    "taxonomy_phylum": "Phylum",
    "taxonomy_class": "Class",
    "taxonomy_order": "Order",
    "taxonomy_family": "Family",
    "taxonomy_genus": "Genus",
    "taxonomy_species": "Species",
}

_DEFAULT_RELEASE_TOKEN = "latest_approved"
_DEFAULT_METHOD_TOKEN = "current"
_DEFAULT_METRIC = "value"


@dataclass(frozen=True)
class IndicatorAnalyticsContext:
    indicator: Indicator
    user: object
    series: list[IndicatorDataSeries]
    points: list[IndicatorDataPoint]
    agg: str
    metric: str
    geo_type: str
    geo_code: str
    start_year: int | None
    end_year: int | None
    selected_year: int | None
    report_cycle: ReportingCycle | None
    release: DatasetRelease | None
    release_param: str
    method_link: IndicatorMethodologyVersionLink | None
    method_param: str
    available_dimensions: list[dict]
    available_years: list[int]
    dimension_filters: dict[str, str]
    taxonomy_level: str
    taxonomy_path: list[str]

    @property
    def units(self) -> list[str]:
        return sorted({str(row.unit or "").strip() for row in self.series if str(row.unit or "").strip()})


def resolve_indicator_analytics_context(indicator: Indicator, user, params, *, default_agg: str = "year") -> IndicatorAnalyticsContext:
    agg = str(params.get("agg") or default_agg or "year").strip().lower()
    metric = str(params.get("metric") or _DEFAULT_METRIC).strip().lower() or _DEFAULT_METRIC
    geo_type = str(params.get("geo_type") or "national").strip().lower() or "national"
    geo_code = str(params.get("geo_code") or "").strip()
    selected_year = _parse_int(params.get("year"))

    report_cycle = _resolve_report_cycle(params.get("report_cycle"))
    requested_start_year = _parse_int(params.get("start_year"))
    requested_end_year = _parse_int(params.get("end_year"))
    if selected_year is not None:
        requested_start_year = selected_year
        requested_end_year = selected_year
    if report_cycle and requested_start_year is None:
        requested_start_year = report_cycle.start_date.year
    if report_cycle and requested_end_year is None:
        requested_end_year = report_cycle.end_date.year
    if requested_start_year and requested_end_year and requested_start_year > requested_end_year:
        requested_start_year, requested_end_year = requested_end_year, requested_start_year

    series_qs = indicator_data_series_for_user(user).filter(indicator=indicator).order_by("title", "uuid")
    series = list(series_qs)
    points_qs = (
        indicator_data_points_for_user(user)
        .filter(series__in=series_qs)
        .select_related("series", "spatial_unit", "spatial_layer", "dataset_release", "programme_run")
        .order_by("year", "id")
    )

    release_param = str(params.get("release") or _DEFAULT_RELEASE_TOKEN).strip() or _DEFAULT_RELEASE_TOKEN
    release = _resolve_release(points_qs, release_param)
    if release is not None:
        points_qs = points_qs.filter(dataset_release=release)
    elif release_param not in {"", _DEFAULT_RELEASE_TOKEN}:
        raise ValidationError("Requested dataset release is not available for this indicator.")

    method_param = str(params.get("method") or _DEFAULT_METHOD_TOKEN).strip() or _DEFAULT_METHOD_TOKEN
    method_link = _resolve_method_link(indicator, method_param)
    if method_link is None and method_param not in {"", _DEFAULT_METHOD_TOKEN}:
        raise ValidationError("Requested methodology version is not available for this indicator.")

    if requested_start_year is not None:
        points_qs = points_qs.filter(year__gte=requested_start_year)
    if requested_end_year is not None:
        points_qs = points_qs.filter(year__lte=requested_end_year)

    points = list(points_qs)
    if geo_code and geo_type != "national":
        geo_code_lower = geo_code.lower()
        points = [
            point
            for point in points
            if str(_dimension_bucket(point, geo_type)[0] or "").strip().lower() == geo_code_lower
        ]

    available_dimensions = list_indicator_dimensions(indicator=indicator, user=user, points=points, series=series)
    dimension_filters, taxonomy_level, taxonomy_path = _resolve_dimension_filters(params, available_dimensions)
    if dimension_filters:
        points = _filter_points_by_dimensions(points, dimension_filters)

    available_years = sorted({point.year for point in points})
    if selected_year is None and available_years:
        selected_year = available_years[-1]

    available_dimensions = list_indicator_dimensions(indicator=indicator, user=user, points=points, series=series)

    return IndicatorAnalyticsContext(
        indicator=indicator,
        user=user,
        series=series,
        points=points,
        agg=agg,
        metric=metric,
        geo_type=geo_type,
        geo_code=geo_code,
        start_year=requested_start_year,
        end_year=requested_end_year,
        selected_year=selected_year,
        report_cycle=report_cycle,
        release=release,
        release_param=release_param,
        method_link=method_link,
        method_param=method_param,
        available_dimensions=available_dimensions,
        available_years=available_years,
        dimension_filters=dimension_filters,
        taxonomy_level=taxonomy_level,
        taxonomy_path=taxonomy_path,
    )


def build_indicator_series_payload(context: IndicatorAnalyticsContext) -> dict:
    grouped: dict[tuple[str | int, str], list[IndicatorDataPoint]] = defaultdict(list)
    for point in context.points:
        bucket, label = _dimension_bucket(point, context.agg)
        if bucket in {None, ""}:
            bucket, label = "UNKNOWN", "Unknown"
        grouped[(bucket, label or str(bucket))].append(point)

    rows = []
    for (bucket, label), points in sorted(grouped.items(), key=lambda item: _bucket_sort_key(item[0][0])):
        numeric_values = [float(point.value_numeric) for point in points if point.value_numeric is not None]
        rows.append(
            {
                "bucket": bucket,
                "label": label,
                "count": len(points),
                "numeric_mean": (sum(numeric_values) / len(numeric_values)) if numeric_values else None,
                "numeric_sum": sum(numeric_values) if numeric_values else None,
                "values": [_serialize_point(point) for point in points],
            }
        )

    return {
        "indicator_uuid": str(context.indicator.uuid),
        "aggregation": context.agg,
        "meta": _context_meta(context),
        "data": rows,
        "results": rows,
    }


def build_indicator_cube_payload(context: IndicatorAnalyticsContext, *, group_by: list[str], measure: str = "value", top_n: int | None = None) -> dict:
    dimensions = [str(item or "").strip().lower() for item in group_by if str(item or "").strip()]
    if not dimensions:
        dimensions = [context.agg or "year"]
    measure = str(measure or "value").strip().lower() or "value"

    grouped: dict[tuple, list[IndicatorDataPoint]] = defaultdict(list)
    dimension_labels: dict[str, str] = {}
    for point in context.points:
        key_parts = []
        for dimension in dimensions:
            bucket, label = _dimension_bucket(point, dimension)
            if bucket in {None, ""}:
                bucket, label = "UNKNOWN", "Unknown"
            key_parts.append((bucket, label))
            dimension_labels[dimension] = _dimension_label(dimension)
        grouped[tuple(key_parts)].append(point)

    rows = []
    for key, points in grouped.items():
        numeric_values = [float(point.value_numeric) for point in points if point.value_numeric is not None]
        row = {
            "value": _measure_value(points, numeric_values, measure),
            "count": len(points),
            "statusFlags": {
                "has_uncertainty": any(bool(str(point.uncertainty or "").strip()) for point in points),
                "has_release": any(point.dataset_release_id for point in points),
                "has_spatial": any(point.spatial_unit_id or point.spatial_layer_id for point in points),
            },
        }
        for index, dimension in enumerate(dimensions):
            bucket, label = key[index]
            row[dimension] = bucket
            row[f"{dimension}_label"] = label
        rows.append(row)

    rows.sort(key=lambda row: (-float(row["value"] or 0),) + tuple(str(row.get(dim) or "") for dim in dimensions))
    if top_n:
        rows = rows[:top_n]

    return {
        "indicator_uuid": str(context.indicator.uuid),
        "rows": rows,
        "meta": {
            **_context_meta(context),
            "dimensions": [
                {"id": dimension, "label": dimension_labels.get(dimension, _dimension_label(dimension))}
                for dimension in dimensions
            ],
            "measure": measure,
            "applied_filters": {
                "report_cycle": context.report_cycle.code if context.report_cycle else None,
                "release": str(context.release.uuid) if context.release else None,
                "method": (
                    str(context.method_link.methodology_version.uuid)
                    if context.method_link and context.method_link.methodology_version_id
                    else None
                ),
                "geo_type": context.geo_type,
                "geo_code": context.geo_code or None,
                "start_year": context.start_year,
                "end_year": context.end_year,
                "dimension_filters": context.dimension_filters,
                "taxonomy_level": context.taxonomy_level or None,
                "taxonomy_path": context.taxonomy_path,
            },
            "provenance_keys": _provenance_keys(context.points),
        },
    }


def list_indicator_dimensions(*, indicator: Indicator | None = None, user=None, points: list[IndicatorDataPoint] | None = None, series: list[IndicatorDataSeries] | None = None) -> list[dict]:
    if indicator is not None and (points is None or series is None):
        series_qs = indicator_data_series_for_user(user).filter(indicator=indicator).order_by("title", "uuid")
        series = list(series_qs)
        points = list(
            indicator_data_points_for_user(user)
            .filter(series__in=series_qs)
            .select_related("series", "spatial_unit", "dataset_release")
            .order_by("year", "id")
        )
    points = points or []
    series = series or []

    observed = {
        "year": {
            "id": "year",
            "label": "Year",
            "type": "time",
            "allowed_levels": ["year"],
            "join_key": "year",
            "sort_order": 10,
        }
    }

    if any(point.dataset_release_id for point in points):
        observed["release"] = {
            "id": "release",
            "label": "Dataset release",
            "type": "categorical",
            "allowed_levels": [],
            "join_key": "dataset_release_uuid",
            "sort_order": 15,
        }

    for dimension_id, keys in _TAXONOMY_DIMENSIONS.items():
        if _points_have_any_key(points, keys):
            observed[dimension_id] = {
                "id": dimension_id,
                "label": _dimension_label(dimension_id),
                "type": "hierarchy",
                "allowed_levels": [item.replace("taxonomy_", "") for item in _TAXONOMY_DIMENSIONS.keys()],
                "join_key": keys[0],
                "sort_order": 40,
            }

    if any(row["id"].startswith("taxonomy_") for row in observed.values()):
        observed["taxonomy"] = {
            "id": "taxonomy",
            "label": "Taxonomy",
            "type": "hierarchy",
            "allowed_levels": [item.replace("taxonomy_", "") for item in _TAXONOMY_DIMENSIONS.keys()],
            "join_key": "taxonomy",
            "sort_order": 35,
        }

    for dimension_id, pairs in _GEO_DIMENSIONS.items():
        if _points_have_any_key(points, [item[0] for item in pairs] + [item[1] for item in pairs]):
            observed[dimension_id] = {
                "id": dimension_id,
                "label": _dimension_label(dimension_id),
                "type": "geo",
                "allowed_levels": [dimension_id],
                "join_key": pairs[0][0],
                "sort_order": 20,
            }

    for dimension_id, pairs in _CATEGORY_DIMENSIONS.items():
        if _points_have_any_key(points, [item[0] for item in pairs] + [item[1] for item in pairs]):
            observed[dimension_id] = {
                "id": dimension_id,
                "label": _dimension_label(dimension_id),
                "type": "categorical",
                "allowed_levels": [],
                "join_key": pairs[0][0],
                "sort_order": 30,
            }

    if any(point.value_text for point in points):
        observed["value_text"] = {
            "id": "value_text",
            "label": "Category",
            "type": "categorical",
            "allowed_levels": [],
            "join_key": "value_text",
            "sort_order": 32,
        }

    schema_keys = _schema_keys(series)
    for raw_key in sorted(schema_keys):
        if raw_key in observed:
            continue
        observed[raw_key] = {
            "id": raw_key,
            "label": _dimension_label(raw_key),
            "type": "categorical",
            "allowed_levels": [],
            "join_key": raw_key,
            "sort_order": 50,
        }

    observed_rows = sorted(observed.values(), key=lambda row: (row["sort_order"], row["label"]))
    if indicator is None:
        return observed_rows
    pack = resolve_indicator_pack(indicator)
    return build_pack_dimensions(pack, observed_rows)


def build_indicator_visual_profile(indicator: Indicator, user) -> dict:
    pack = resolve_indicator_pack(indicator)
    context = resolve_indicator_analytics_context(indicator, user, {}, default_agg=pack.get("default_agg") or "year")
    map_layers = _profile_map_layers(indicator, user, context.available_dimensions, pack)
    profile = build_pack_profile(pack, dimensions=context.available_dimensions, map_layers=map_layers, meta=_context_meta(context))
    supported_dimensions = {row["id"] for row in context.available_dimensions}
    numeric_series = any(
        series.value_type in {IndicatorValueType.NUMERIC, IndicatorValueType.PERCENT, IndicatorValueType.INDEX}
        for series in context.series
    )
    available_views = []
    for view in profile["availableViews"]:
        if view == "timeseries" and numeric_series:
            available_views.append(view)
        elif view == "taxonomy" and any(row.startswith("taxonomy_") for row in supported_dimensions):
            available_views.append(view)
        elif view == "distribution" and any(row.get("type") == "categorical" for row in context.available_dimensions):
            available_views.append(view)
        elif view == "matrix" and any(
            definition["xDimension"] in supported_dimensions and definition["yDimension"] in supported_dimensions
            for definition in profile.get("matrixDefinitions", [])
        ):
            available_views.append(view)
        elif view == "binary" and indicator.indicator_type == "binary":
            available_views.append(view)
    profile["availableViews"] = available_views or ["timeseries"]
    if profile["defaultView"] not in profile["availableViews"]:
        profile["defaultView"] = profile["availableViews"][0]
    profile["indicator_uuid"] = str(indicator.uuid)
    return profile


def build_indicator_map_payload(context: IndicatorAnalyticsContext, *, layer_code: str = "", bbox=None, limit: int = 5000) -> dict:
    layer, layer_spec = _resolve_map_layer(context, layer_code)
    if layer is None:
        raise ValidationError("No accessible map layer found for this indicator.")
    available_metrics = list(layer_spec.get("availableMetrics") or ["value", "change", "coverage", "uncertainty"])
    selected_metric = context.metric if context.metric in available_metrics else (layer_spec.get("defaultMetric") or available_metrics[0])

    selected_year = context.selected_year
    if selected_year is None:
        return {
            "indicator_uuid": str(context.indicator.uuid),
            "indicator_code": context.indicator.code,
            "year": None,
            "layer_code": layer.layer_code,
            "meta": {
                **_context_meta(context),
                "available_metrics": available_metrics,
                "selected_metric": selected_metric,
                "join_dimension": layer_spec.get("dimensionId") or _map_join_dimension(context, layer, layer_spec),
            },
            "type": "FeatureCollection",
            "features": [],
        }

    current_points = [point for point in context.points if point.year == selected_year]
    prior_year = None
    prior_years = sorted({point.year for point in context.points if point.year < selected_year})
    if prior_years:
        prior_year = prior_years[-1]
    prior_points = [point for point in context.points if prior_year is not None and point.year == prior_year]

    current_metrics = _map_metrics_by_bucket(current_points, context.geo_type)
    prior_metrics = _map_metrics_by_bucket(prior_points, context.geo_type)

    _, payload = spatial_feature_collection(
        user=context.user,
        layer_code=layer.layer_code,
        bbox=bbox,
        limit=limit,
        offset=0,
    )

    join_dimension = layer_spec.get("dimensionId") or _map_join_dimension(context, layer, layer_spec)
    min_value = None
    max_value = None
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        bucket = _feature_bucket(properties, join_dimension)
        current = current_metrics.get(bucket, {})
        prior = prior_metrics.get(bucket, {})
        value = current.get("value")
        change = (value - prior["value"]) if value is not None and prior.get("value") is not None else None
        coverage = current.get("count")
        uncertainty = current.get("uncertainty")
        if value is not None:
            min_value = value if min_value is None else min(min_value, value)
            max_value = value if max_value is None else max(max_value, value)
        properties["indicator_code"] = context.indicator.code
        properties["indicator_year"] = selected_year
        properties["indicator_value"] = value
        properties["indicator_change"] = change
        properties["indicator_coverage"] = coverage
        properties["indicator_uncertainty"] = uncertainty
        properties["indicator_metric_value"] = {
            "value": value,
            "change": change,
            "coverage": coverage,
            "uncertainty": uncertainty,
        }.get(selected_metric, value)
        properties["indicator_metric"] = selected_metric
        properties["indicator_selected"] = bool(
            context.geo_code and str(bucket or "").strip().lower() == context.geo_code.strip().lower()
        )

    payload["indicator_uuid"] = str(context.indicator.uuid)
    payload["indicator_code"] = context.indicator.code
    payload["year"] = selected_year
    payload["layer_code"] = layer.layer_code
    payload["meta"] = {
        **_context_meta(context),
        "available_metrics": available_metrics,
        "selected_metric": selected_metric,
        "legend": {
            "metric": selected_metric,
            "min": min_value,
            "max": max_value,
        },
        "join_dimension": join_dimension,
        "compare_year": prior_year,
    }
    return payload


def build_indicator_audit_payload(indicator: Indicator, user) -> dict:
    series_uuids = list(
        indicator_data_series_for_user(user)
        .filter(indicator=indicator)
        .values_list("uuid", flat=True)
    )
    events = (
        AuditEvent.objects.filter(Q(object_uuid=indicator.uuid) | Q(object_uuid__in=series_uuids))
        .select_related("actor")
        .order_by("-created_at", "-id")[:100]
    )
    return {
        "indicator_uuid": str(indicator.uuid),
        "events": [
            {
                "event_id": event.id,
                "timestamp": event.created_at.isoformat() if event.created_at else None,
                "actor": event.actor.username if event.actor_id else None,
                "action": event.action,
                "event_type": event.event_type,
                "object_type": event.object_type,
                "object_uuid": str(event.object_uuid) if event.object_uuid else None,
                "from_state": (
                    event.metadata.get("from_status")
                    or event.metadata.get("state_from")
                    or event.metadata.get("previous_status")
                ),
                "to_state": event.metadata.get("status") or event.metadata.get("state_to"),
                "notes": event.metadata.get("note"),
                "metadata": event.metadata,
            }
            for event in events
        ],
    }


def list_global_dimensions() -> list[dict]:
    return list_pack_dimensions()


def _resolve_report_cycle(value) -> ReportingCycle | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    query = Q(code__iexact=raw)
    try:
        UUID(raw)
        query |= Q(uuid=raw)
    except (TypeError, ValueError):
        pass
    return ReportingCycle.objects.filter(query).order_by("-is_active", "code").first()


def _resolve_release(points_qs, release_param: str) -> DatasetRelease | None:
    release_candidates = (
        DatasetRelease.objects.filter(id__in=points_qs.exclude(dataset_release_id__isnull=True).values_list("dataset_release_id", flat=True))
        .order_by("-release_date", "-created_at", "-id")
    )
    if release_param in {"", _DEFAULT_RELEASE_TOKEN}:
        return release_candidates.filter(status__in=[LifecycleStatus.APPROVED, LifecycleStatus.PUBLISHED]).first()
    query = Q(version__iexact=release_param)
    try:
        UUID(release_param)
        query |= Q(uuid=release_param)
    except (TypeError, ValueError):
        pass
    release = release_candidates.filter(query).first()
    if release:
        return release
    for candidate in release_candidates:
        if release_param in {str(candidate.uuid), str(candidate.version or "").strip()}:
            return candidate
    return None


def _resolve_method_link(indicator: Indicator, method_param: str) -> IndicatorMethodologyVersionLink | None:
    links = (
        IndicatorMethodologyVersionLink.objects.filter(indicator=indicator, is_active=True)
        .select_related("methodology_version", "methodology_version__methodology")
        .order_by("-is_primary", "-methodology_version__effective_date", "-methodology_version__created_at", "-id")
    )
    if method_param in {"", _DEFAULT_METHOD_TOKEN}:
        return links.first()
    for link in links:
        version = link.methodology_version
        if not version:
            continue
        if method_param in {
            str(version.uuid),
            str(version.version or "").strip(),
            str(version.methodology.methodology_code or "").strip(),
        }:
            return link
    return None


def _serialize_point(point: IndicatorDataPoint) -> dict:
    return {
        "uuid": str(point.uuid),
        "year": point.year,
        "value_numeric": float(point.value_numeric) if point.value_numeric is not None else None,
        "value_text": point.value_text,
        "uncertainty": point.uncertainty,
        "disaggregation": point.disaggregation,
        "spatial_resolution": point.spatial_resolution or point.series.spatial_resolution,
        "dataset_release": (
            {
                "uuid": str(point.dataset_release.uuid),
                "version": point.dataset_release.version,
                "status": point.dataset_release.status,
            }
            if point.dataset_release_id
            else None
        ),
        "spatial_unit": (
            {
                "uuid": str(point.spatial_unit.uuid),
                "unit_code": point.spatial_unit.unit_code,
                "name": point.spatial_unit.name,
            }
            if point.spatial_unit_id
            else None
        ),
        "spatial_layer": (
            {
                "uuid": str(point.spatial_layer.uuid),
                "layer_code": point.spatial_layer.layer_code,
                "title": point.spatial_layer.title or point.spatial_layer.name,
            }
            if point.spatial_layer_id
            else None
        ),
    }


def _context_meta(context: IndicatorAnalyticsContext) -> dict:
    return {
        "release_used": (
            {
                "param": context.release_param,
                "uuid": str(context.release.uuid),
                "version": context.release.version,
                "status": context.release.status,
                "release_date": context.release.release_date.isoformat() if context.release.release_date else None,
            }
            if context.release
            else {"param": context.release_param, "uuid": None, "version": None, "status": None, "release_date": None}
        ),
        "method_used": (
            {
                "param": context.method_param,
                "uuid": str(context.method_link.methodology_version.uuid),
                "version": context.method_link.methodology_version.version,
                "methodology_code": context.method_link.methodology_version.methodology.methodology_code,
                "methodology_title": context.method_link.methodology_version.methodology.title,
                "applies_to_points": False,
            }
            if context.method_link and context.method_link.methodology_version_id
            else {"param": context.method_param, "uuid": None, "version": None, "methodology_code": None, "methodology_title": None, "applies_to_points": False}
        ),
        "report_cycle": (
            {
                "uuid": str(context.report_cycle.uuid),
                "code": context.report_cycle.code,
                "title": context.report_cycle.title,
                "start_date": context.report_cycle.start_date.isoformat(),
                "end_date": context.report_cycle.end_date.isoformat(),
            }
            if context.report_cycle
            else None
        ),
        "time_range": {
            "start_year": context.start_year,
            "end_year": context.end_year,
            "selected_year": context.selected_year,
            "available_years": context.available_years,
        },
        "agg": context.agg,
        "geo_filters": {
            "geo_type": context.geo_type,
            "geo_code": context.geo_code or None,
        },
        "units": context.units,
        "series_count": len(context.series),
        "point_count": len(context.points),
        "dimensions": context.available_dimensions,
        "selection_filters": {
            "dimensions": context.dimension_filters,
            "taxonomy_level": context.taxonomy_level or None,
            "taxonomy_path": context.taxonomy_path,
        },
    }


def _dimension_bucket(point: IndicatorDataPoint, dimension: str) -> tuple[str | int | None, str]:
    disaggregation = point.disaggregation or {}
    dimension = str(dimension or "year").strip().lower() or "year"
    if dimension in {"year", "time"}:
        return point.year, str(point.year)
    if dimension == "release":
        if point.dataset_release_id:
            return str(point.dataset_release.uuid), point.dataset_release.version
        return None, ""
    if dimension in {"value_text", "category_value"}:
        value_text = str(point.value_text or "").strip()
        return (value_text or None), value_text
    if dimension in _TAXONOMY_DIMENSIONS:
        return _first_present(disaggregation, _TAXONOMY_DIMENSIONS[dimension])
    if dimension == "taxonomy":
        for tax_dimension in reversed(list(_TAXONOMY_DIMENSIONS.keys())):
            value = _first_present(disaggregation, _TAXONOMY_DIMENSIONS[tax_dimension])
            if value[0]:
                return value
        return None, ""
    if dimension in _GEO_DIMENSIONS:
        return _geo_value(point, dimension)
    if dimension in _CATEGORY_DIMENSIONS:
        for code_key, label_key in _CATEGORY_DIMENSIONS[dimension]:
            bucket = str(disaggregation.get(code_key) or "").strip()
            label = str(disaggregation.get(label_key) or bucket).strip()
            if bucket:
                return bucket, label
        return None, ""
    bucket = str(disaggregation.get(dimension) or "").strip()
    label = str(disaggregation.get(f"{dimension}_label") or disaggregation.get(f"{dimension}_name") or bucket).strip()
    if bucket:
        return bucket, label
    return None, ""


def _first_present(disaggregation: dict, keys: list[str]) -> tuple[str | None, str]:
    for key in keys:
        value = str(disaggregation.get(key) or "").strip()
        if value:
            label = str(disaggregation.get(f"{key}_label") or disaggregation.get(f"{key}_name") or value).strip()
            return value, label
    return None, ""


def _geo_value(point: IndicatorDataPoint, dimension: str) -> tuple[str | None, str]:
    disaggregation = point.disaggregation or {}
    for code_key, label_key in _GEO_DIMENSIONS.get(dimension, []):
        bucket = str(disaggregation.get(code_key) or "").strip()
        label = str(disaggregation.get(label_key) or bucket).strip()
        if bucket:
            return bucket, label or bucket
    if point.spatial_unit_id:
        unit_code = str(point.spatial_unit.unit_code or "").strip()
        unit_name = str(point.spatial_unit.name or unit_code).strip()
        if unit_code:
            return unit_code, unit_name
    return None, ""


def _measure_value(points: list[IndicatorDataPoint], numeric_values: list[float], measure: str):
    if measure in {"count", "records"}:
        return len(points)
    if measure in {"sum", "total"}:
        return sum(numeric_values) if numeric_values else len(points)
    if measure in {"mean", "avg", "average", "value"}:
        return (sum(numeric_values) / len(numeric_values)) if numeric_values else len(points)
    return (sum(numeric_values) / len(numeric_values)) if numeric_values else len(points)


def _provenance_keys(points: list[IndicatorDataPoint]) -> dict:
    return {
        "dataset_release_uuids": sorted({str(point.dataset_release.uuid) for point in points if point.dataset_release_id}),
        "programme_run_uuids": sorted({str(point.programme_run.uuid) for point in points if point.programme_run_id}),
        "source_urls": sorted({str(point.source_url).strip() for point in points if str(point.source_url or "").strip()}),
    }


def _bucket_sort_key(value):
    if isinstance(value, int):
        return (0, value)
    raw = str(value or "")
    try:
        return (0, int(raw))
    except ValueError:
        return (1, raw.lower())


def _dimension_label(value: str) -> str:
    if value in _DIMENSION_LABELS:
        return _DIMENSION_LABELS[value]
    return str(value or "").replace("_", " ").strip().title()


def _points_have_any_key(points: list[IndicatorDataPoint], keys: list[str]) -> bool:
    if not points:
        return False
    for point in points:
        disaggregation = point.disaggregation or {}
        for key in keys:
            if str(disaggregation.get(key) or "").strip():
                return True
    return False


def _schema_keys(series: list[IndicatorDataSeries]) -> set[str]:
    keys: set[str] = set()
    for row in series:
        schema = row.disaggregation_schema or {}
        keys.update(_collect_schema_keys(schema))
    return keys


def _collect_schema_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.strip():
                keys.add(key.strip())
            keys.update(_collect_schema_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_collect_schema_keys(item))
    return keys


def _profile_map_layers(indicator: Indicator, user, dimensions: list[dict], pack: dict) -> list[dict]:
    visible_codes = []
    specs_by_code = {}
    for spec in _pack_layer_specs(pack):
        for code in spec["layerCodes"]:
            specs_by_code[code] = spec
            visible_codes.append(code)
    input_requirement = getattr(indicator, "input_requirement", None)
    if input_requirement:
        visible_codes.extend(input_requirement.required_map_layers.values_list("layer_code", flat=True))
    visible_codes = [item for item in dict.fromkeys(visible_codes) if item]
    if not visible_codes:
        return []
    visible_layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.filter(layer_code__in=visible_codes),
        user,
    )
    layer_map = {layer.layer_code: layer for layer in visible_layers}
    resolved = []
    for code in visible_codes:
        layer = layer_map.get(code)
        if layer is None:
            continue
        spec = specs_by_code.get(layer.layer_code) or {
            "title": layer.title or layer.name,
            "joinKey": "province_code",
            "dimensionId": "province",
            "availableMetrics": ["value", "change", "coverage", "uncertainty"],
            "defaultMetric": "value",
        }
        resolved.append(
            {
                "layerCode": layer.layer_code,
                "title": spec.get("title") or layer.title or layer.name,
                "joinKey": spec.get("joinKey") or "province_code",
                "dimensionId": spec.get("dimensionId") or _join_key_dimension(spec.get("joinKey") or "province_code"),
                "availableMetrics": list(spec.get("availableMetrics") or ["value", "change", "coverage", "uncertainty"]),
                "defaultMetric": spec.get("defaultMetric") or "value",
            }
        )
    return resolved


def _pack_layer_specs(pack: dict) -> list[dict]:
    specs = []
    for spec in pack.get("map_layers", []):
        candidate_codes = [item for item in dict.fromkeys(spec.get("layerCodes") or []) if item]
        if not candidate_codes:
            continue
        join_key = spec.get("joinKey") or "province_code"
        specs.append(
            {
                "layerCodes": candidate_codes,
                "title": spec.get("title") or "Indicator map",
                "joinKey": join_key,
                "dimensionId": _join_key_dimension(join_key),
                "availableMetrics": list(spec.get("availableMetrics") or ["value", "change", "coverage", "uncertainty"]),
                "defaultMetric": spec.get("defaultMetric") or "value",
            }
        )
    return specs


def _join_key_dimension(join_key: str) -> str:
    if join_key == "municipality_code":
        return "municipality"
    if join_key == "biome_code":
        return "biome"
    if join_key == "ecoregion_code":
        return "ecoregion"
    return "province"


def _resolve_map_layer(context: IndicatorAnalyticsContext, layer_code: str) -> tuple[SpatialLayer | None, dict]:
    pack = resolve_indicator_pack(context.indicator)
    specs = _pack_layer_specs(pack)
    input_requirement = getattr(context.indicator, "input_requirement", None)
    candidate_codes: list[str] = []
    specs_by_code: dict[str, dict] = {}
    for spec in specs:
        for code in spec["layerCodes"]:
            specs_by_code[code] = spec
            candidate_codes.append(code)
    if layer_code:
        candidate_codes.insert(0, layer_code)
    if input_requirement:
        candidate_codes.extend(input_requirement.required_map_layers.order_by("layer_code", "id").values_list("layer_code", flat=True))
    if context.geo_type == "province" or _points_have_geo(context.points, "province"):
        candidate_codes.extend(["ZA_PROVINCES_NE", "ZA_PROVINCES"])
    candidate_codes = [item for item in dict.fromkeys(candidate_codes) if item]
    if not candidate_codes:
        return None, {}
    visible_layers = filter_spatial_layers_for_user(
        SpatialLayer.objects.filter(layer_code__in=candidate_codes),
        context.user,
    )
    layer_map = {layer.layer_code: layer for layer in visible_layers}
    layer = next((layer_map.get(code) for code in candidate_codes if layer_map.get(code) is not None), None)
    if layer is None:
        return None, {}
    return layer, specs_by_code.get(layer.layer_code) or {}


def _points_have_geo(points: list[IndicatorDataPoint], dimension: str) -> bool:
    return any(_dimension_bucket(point, dimension)[0] for point in points)


def _map_join_dimension(context: IndicatorAnalyticsContext, layer: SpatialLayer, layer_spec: dict | None = None) -> str:
    if layer_spec and layer_spec.get("dimensionId"):
        return str(layer_spec["dimensionId"])
    if context.geo_type in {"province", "municipality"}:
        return context.geo_type
    if _points_have_geo(context.points, "province"):
        return "province"
    if _points_have_geo(context.points, "municipality"):
        return "municipality"
    if "municipality" in str(layer.layer_code or "").lower():
        return "municipality"
    return "province"


def _map_metrics_by_bucket(points: list[IndicatorDataPoint], geo_type: str) -> dict[str, dict]:
    grouped: dict[str, list[IndicatorDataPoint]] = defaultdict(list)
    dimension = geo_type if geo_type != "national" else "province"
    for point in points:
        bucket, _ = _dimension_bucket(point, dimension)
        if bucket:
            grouped[str(bucket)].append(point)
    metrics = {}
    for bucket, rows in grouped.items():
        numeric_values = [float(point.value_numeric) for point in rows if point.value_numeric is not None]
        metrics[bucket] = {
            "value": (sum(numeric_values) / len(numeric_values)) if numeric_values else None,
            "count": len(rows),
            "uncertainty": (
                sum(1 for point in rows if str(point.uncertainty or "").strip()) / len(rows) if rows else 0
            ),
        }
    return metrics


def _feature_bucket(properties: dict, join_dimension: str) -> str:
    if join_dimension == "municipality":
        return str(
            properties.get("municipality_code")
            or properties.get("municipality")
            or properties.get("feature_key")
            or properties.get("feature_id")
            or ""
        ).strip()
    return str(
        properties.get("province_code")
        or properties.get("province")
        or properties.get("feature_key")
        or properties.get("feature_id")
        or ""
    ).strip()


def _parse_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_dimension_filters(params, available_dimensions: list[dict]) -> tuple[dict[str, str], str, list[str]]:
    filters: dict[str, str] = {}
    dimension = str(params.get("dim") or "").strip().lower()
    dimension_value = str(params.get("dim_value") or "").strip()
    if dimension and dimension_value:
        filters[dimension] = dimension_value
    compare_dimension = str(params.get("compare") or "").strip().lower()
    left_value = str(params.get("left") or "").strip()
    right_value = str(params.get("right") or "").strip()
    if compare_dimension and right_value:
        filters[compare_dimension] = right_value
    if dimension and left_value and dimension not in filters:
        filters[dimension] = left_value

    taxonomy_level = str(params.get("tax_level") or "").strip().lower()
    taxonomy_code = str(params.get("tax_code") or "").strip()
    if not taxonomy_code:
        return filters, taxonomy_level, []

    available_taxonomy_levels = [
        row["id"].replace("taxonomy_", "")
        for row in available_dimensions
        if str(row.get("id") or "").startswith("taxonomy_")
    ]
    available_taxonomy_levels.sort(key=lambda level: _taxonomy_level_order(level))
    taxonomy_path = [segment.strip() for segment in taxonomy_code.split(">") if segment.strip()]
    if not available_taxonomy_levels or not taxonomy_path:
        return filters, taxonomy_level, taxonomy_path

    keyed_segments = []
    for segment in taxonomy_path:
        if ":" not in segment:
            keyed_segments = []
            break
        level, code = segment.split(":", 1)
        normalized_level = level.replace("taxonomy_", "").strip().lower()
        normalized_code = code.strip()
        if not normalized_level or not normalized_code:
            keyed_segments = []
            break
        keyed_segments.append((normalized_level, normalized_code))

    if keyed_segments:
        for level, code in keyed_segments:
            if level in available_taxonomy_levels:
                filters[f"taxonomy_{level}"] = code
        return filters, taxonomy_level, taxonomy_path

    max_index = len(taxonomy_path)
    if taxonomy_level in available_taxonomy_levels:
        max_index = min(max_index, available_taxonomy_levels.index(taxonomy_level) + 1)

    for level, code in zip(available_taxonomy_levels[:max_index], taxonomy_path[:max_index]):
        filters[f"taxonomy_{level}"] = code
    return filters, taxonomy_level, taxonomy_path[:max_index]


def _filter_points_by_dimensions(points: list[IndicatorDataPoint], filters: dict[str, str]) -> list[IndicatorDataPoint]:
    if not filters:
        return points
    rows = points
    for dimension, expected in filters.items():
        expected_normalized = str(expected or "").strip().lower()
        rows = [
            point
            for point in rows
            if str(_dimension_bucket(point, dimension)[0] or "").strip().lower() == expected_normalized
        ]
    return rows


def _taxonomy_level_order(level: str) -> int:
    ordered = [item.replace("taxonomy_", "") for item in _TAXONOMY_DIMENSIONS.keys()]
    try:
        return ordered.index(level)
    except ValueError:
        return len(ordered) + 1
