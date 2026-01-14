from rest_framework import serializers, viewsets
from rest_framework.routers import DefaultRouter

from nbms_app.models import Evidence
from nbms_app.services.authorization import filter_queryset_for_user


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ["uuid", "title", "evidence_type", "source_url", "status", "sensitivity"]


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EvidenceSerializer

    def get_queryset(self):
        queryset = Evidence.objects.select_related("organisation", "created_by").order_by("title")
        return filter_queryset_for_user(queryset, self.request.user, perm="nbms_app.view_evidence")


api_router = DefaultRouter()
api_router.register("evidence", EvidenceViewSet, basename="evidence")
