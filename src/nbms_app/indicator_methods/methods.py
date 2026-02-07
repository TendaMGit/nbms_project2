from __future__ import annotations

from django.db.models import Avg

from nbms_app.indicator_methods.base import BaseIndicatorMethod, MethodResult
from nbms_app.models import BinaryIndicatorResponse, IndicatorDataPoint, IndicatorFrameworkIndicatorLink, SpatialFeature


class BinaryQuestionnaireMethod(BaseIndicatorMethod):
    key = "binary_questionnaire_aggregator"

    def run(self, context):
        framework_indicator_ids = list(
            IndicatorFrameworkIndicatorLink.objects.filter(indicator=context.indicator, is_active=True).values_list(
                "framework_indicator_id",
                flat=True,
            )
        )
        if not framework_indicator_ids:
            return MethodResult(
                status="blocked",
                output={"reason": "No framework indicator mapping for binary aggregation."},
                error_message="Indicator has no framework indicator mapping.",
            )

        responses = BinaryIndicatorResponse.objects.filter(
            question__framework_indicator_id__in=framework_indicator_ids
        ).select_related("question")
        total = responses.count()
        completed = 0
        for item in responses:
            value = item.response
            if value in (True, False):
                completed += 1
            elif isinstance(value, dict) and value:
                completed += 1
            elif isinstance(value, list) and value:
                completed += 1
        completion_pct = round((completed / total) * 100, 2) if total else 0.0
        state = "ready" if completion_pct >= 80 else ("partial" if completion_pct > 0 else "blocked")
        return MethodResult(
            status="succeeded",
            output={
                "method": self.key,
                "response_count": total,
                "completed_response_count": completed,
                "completion_percent": completion_pct,
                "progress_state": state,
            },
        )


class CsvAggregationMethod(BaseIndicatorMethod):
    key = "csv_import_aggregation"

    def run(self, context):
        points_qs = IndicatorDataPoint.objects.filter(series__indicator=context.indicator).order_by("year", "id")
        if not points_qs.exists():
            return MethodResult(
                status="blocked",
                output={"reason": "No datapoints available for CSV aggregation."},
                error_message="No indicator datapoints found.",
            )
        by_year = (
            points_qs.values("year")
            .annotate(mean_numeric=Avg("value_numeric"))
            .order_by("year")
        )
        output_rows = [
            {"year": row["year"], "mean_numeric": float(row["mean_numeric"]) if row["mean_numeric"] is not None else None}
            for row in by_year
        ]
        return MethodResult(
            status="succeeded",
            output={
                "method": self.key,
                "row_count": len(output_rows),
                "aggregated_by_year": output_rows,
            },
        )


class SpatialOverlayMethod(BaseIndicatorMethod):
    key = "spatial_overlay_area_by_province"

    def run(self, context):
        features = SpatialFeature.objects.filter(indicator=context.indicator).order_by("province_code", "feature_key")
        if not features.exists():
            return MethodResult(
                status="blocked",
                output={"reason": "No spatial features linked to indicator."},
                error_message="No spatial features found for indicator.",
            )

        province_totals = {}
        for feature in features:
            province = feature.province_code or "UNSPECIFIED"
            area = feature.properties_json.get("area_ha") if isinstance(feature.properties_json, dict) else None
            area_value = float(area) if area is not None else 0.0
            province_totals[province] = province_totals.get(province, 0.0) + area_value

        output_rows = [
            {"province": province, "area_ha": round(total, 3)}
            for province, total in sorted(province_totals.items(), key=lambda item: item[0])
        ]
        return MethodResult(
            status="succeeded",
            output={
                "method": self.key,
                "feature_count": features.count(),
                "province_area_totals": output_rows,
            },
        )


class BirdieApiConnectorMethod(BaseIndicatorMethod):
    key = "birdie_api_connector"

    def run(self, context):
        points_qs = IndicatorDataPoint.objects.filter(
            series__indicator=context.indicator,
            value_numeric__isnull=False,
        ).order_by("year", "id")
        if not points_qs.exists():
            return MethodResult(
                status="blocked",
                output={"reason": "No BIRDIE datapoints available for indicator."},
                error_message="No BIRDIE datapoints available.",
            )
        latest_two = list(points_qs.order_by("-year", "-id")[:2])
        latest = latest_two[0] if latest_two else None
        previous = latest_two[1] if len(latest_two) > 1 else None
        trend = "flat"
        if previous and latest and latest.value_numeric is not None and previous.value_numeric is not None:
            if latest.value_numeric > previous.value_numeric:
                trend = "up"
            elif latest.value_numeric < previous.value_numeric:
                trend = "down"
        return MethodResult(
            status="succeeded",
            output={
                "method": self.key,
                "point_count": points_qs.count(),
                "latest_year": latest.year if latest else None,
                "latest_value": float(latest.value_numeric) if latest and latest.value_numeric is not None else None,
                "trend": trend,
            },
        )
