from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from nbms_app.models import (
    DatasetCatalog,
    DatasetRelease,
    Evidence,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    NationalTarget,
)
from nbms_app.services.audit import audit_sensitive_access
from nbms_app.services.authorization import filter_queryset_for_user
from nbms_app.services.catalog_access import filter_dataset_catalog_for_user


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ["uuid", "title", "evidence_type", "source_url", "status", "sensitivity"]


class AuditReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    def get_object(self):
        obj = super().get_object()
        audit_sensitive_access(self.request, obj, action="api_view")
        return obj

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            for obj in page:
                audit_sensitive_access(request, obj, action="api_list")
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        items = list(queryset)
        for obj in items:
            audit_sensitive_access(request, obj, action="api_list")
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class EvidenceViewSet(AuditReadOnlyModelViewSet):
    serializer_class = EvidenceSerializer

    def get_queryset(self):
        queryset = Evidence.objects.select_related("organisation", "created_by").order_by("title")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_evidence")


class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = ["uuid", "code", "title", "description", "status", "sensitivity"]


class FrameworkGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameworkGoal
        fields = ["uuid", "framework", "code", "title", "status", "sensitivity", "sort_order"]


class FrameworkTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameworkTarget
        fields = ["uuid", "framework", "goal", "code", "title", "status", "sensitivity"]


class FrameworkIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameworkIndicator
        fields = ["uuid", "framework", "framework_target", "code", "title", "indicator_type", "status", "sensitivity"]


class NationalTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = NationalTarget
        fields = ["uuid", "code", "title", "status", "sensitivity"]


class IndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = ["uuid", "code", "title", "national_target", "indicator_type", "status", "sensitivity"]


class DatasetCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetCatalog
        fields = ["uuid", "dataset_code", "title", "description", "access_level", "is_active"]


class DatasetReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetRelease
        fields = ["uuid", "dataset", "version", "release_date", "status", "sensitivity"]


class FrameworkViewSet(AuditReadOnlyModelViewSet):
    serializer_class = FrameworkSerializer

    def get_queryset(self):
        queryset = Framework.objects.order_by("code")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_framework")


class FrameworkGoalViewSet(AuditReadOnlyModelViewSet):
    serializer_class = FrameworkGoalSerializer

    def get_queryset(self):
        queryset = FrameworkGoal.objects.select_related("framework").order_by("framework__code", "sort_order", "code")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_frameworkgoal")


class FrameworkTargetViewSet(AuditReadOnlyModelViewSet):
    serializer_class = FrameworkTargetSerializer

    def get_queryset(self):
        queryset = FrameworkTarget.objects.select_related("framework", "goal").order_by("framework__code", "code")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_frameworktarget")


class FrameworkIndicatorViewSet(AuditReadOnlyModelViewSet):
    serializer_class = FrameworkIndicatorSerializer

    def get_queryset(self):
        queryset = FrameworkIndicator.objects.select_related("framework", "framework_target").order_by("framework__code", "code")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_frameworkindicator")


class NationalTargetViewSet(AuditReadOnlyModelViewSet):
    serializer_class = NationalTargetSerializer

    def get_queryset(self):
        queryset = NationalTarget.objects.select_related("organisation", "created_by").order_by("code")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_nationaltarget")


class IndicatorViewSet(AuditReadOnlyModelViewSet):
    serializer_class = IndicatorSerializer

    def get_queryset(self):
        queryset = Indicator.objects.select_related("national_target", "organisation", "created_by").order_by("code")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_indicator")


class DatasetCatalogViewSet(AuditReadOnlyModelViewSet):
    serializer_class = DatasetCatalogSerializer

    def get_queryset(self):
        queryset = DatasetCatalog.objects.select_related("custodian_org", "producer_org", "sensitivity_class")
        return filter_dataset_catalog_for_user(queryset, self.request.user)


class DatasetReleaseViewSet(AuditReadOnlyModelViewSet):
    serializer_class = DatasetReleaseSerializer

    def get_queryset(self):
        datasets = filter_dataset_catalog_for_user(DatasetCatalog.objects.all(), self.request.user)
        return DatasetRelease.objects.select_related("dataset").filter(dataset__in=datasets)


api_router = DefaultRouter()
api_router.register("evidence", EvidenceViewSet, basename="evidence")
api_router.register("frameworks", FrameworkViewSet, basename="frameworks")
api_router.register("framework-goals", FrameworkGoalViewSet, basename="framework_goals")
api_router.register("framework-targets", FrameworkTargetViewSet, basename="framework_targets")
api_router.register("framework-indicators", FrameworkIndicatorViewSet, basename="framework_indicators")
api_router.register("national-targets", NationalTargetViewSet, basename="national_targets")
api_router.register("indicators", IndicatorViewSet, basename="indicators")
api_router.register("dataset-catalog", DatasetCatalogViewSet, basename="dataset_catalog")
api_router.register("dataset-releases", DatasetReleaseViewSet, basename="dataset_releases")
