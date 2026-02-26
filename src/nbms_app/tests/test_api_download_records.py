from __future__ import annotations

from datetime import date
from decimal import Decimal
import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from nbms_app.models import (
    DownloadRecord,
    DownloadRecordType,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    ReportingCycle,
    ReportingInstance,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
    User,
)


pytestmark = pytest.mark.django_db


def _seed_indicator_series(*, org, sensitivity=SensitivityLevel.PUBLIC):
    target = NationalTarget.objects.create(
        code=f"T-{org.org_code}",
        title=f"Target {org.org_code}",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=sensitivity,
    )
    indicator = Indicator.objects.create(
        code=f"IND-{org.org_code}",
        title=f"Indicator {org.org_code}",
        national_target=target,
        indicator_type=NationalIndicatorType.OTHER,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=sensitivity,
    )
    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="National series",
        unit="index",
        value_type="numeric",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=sensitivity,
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2024,
        value_numeric=Decimal("23.4"),
        disaggregation={"province_code": "WC"},
    )
    return indicator


def test_download_record_list_requires_auth(client):
    response = client.get(reverse("api_download_records"))
    assert response.status_code == 401


def test_download_record_create_list_detail_and_file(client):
    org = Organisation.objects.create(name="Download Org", org_code="DL-ORG")
    user = User.objects.create_user(username="dl_user", password="pass1234", organisation=org, is_staff=True)
    indicator = _seed_indicator_series(org=org)

    client.force_login(user)
    create_response = client.post(
        reverse("api_download_records"),
        data=json.dumps(
            {
                "record_type": "indicator_series",
                "object_type": "indicator",
                "object_uuid": str(indicator.uuid),
                "query_snapshot": {"year_from": 2024, "year_to": 2024},
            }
        ),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    record_uuid = create_response.json()["uuid"]
    assert create_response.json()["landing_url"] == f"/downloads/{record_uuid}"

    list_response = client.get(reverse("api_download_records"))
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["results"][0]["record_type"] == DownloadRecordType.INDICATOR_SERIES

    detail_response = client.get(reverse("api_download_record_detail", args=[record_uuid]))
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["record"]
    assert detail_payload["citation_text"]
    assert detail_payload["file"]["authorized"] is True

    file_response = client.get(reverse("api_download_record_file", args=[record_uuid]))
    assert file_response.status_code == 200
    assert file_response["Content-Type"].startswith("text/csv")
    assert "attachment" in file_response["Content-Disposition"]


def test_download_record_visibility_when_access_is_revoked(client):
    org_a = Organisation.objects.create(name="Org A", org_code="ORG-A")
    org_b = Organisation.objects.create(name="Org B", org_code="ORG-B")
    user = User.objects.create_user(username="dl_owner", password="pass1234", organisation=org_a, is_staff=True)
    indicator = _seed_indicator_series(org=org_a, sensitivity=SensitivityLevel.PUBLIC)

    client.force_login(user)
    create_response = client.post(
        reverse("api_download_records"),
        data=json.dumps(
            {
                "record_type": "indicator_series",
                "object_type": "indicator",
                "object_uuid": str(indicator.uuid),
            }
        ),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    record_uuid = create_response.json()["uuid"]

    # Tighten access after the record has already been created, then move user outside owning org.
    indicator.sensitivity = SensitivityLevel.INTERNAL
    indicator.save(update_fields=["sensitivity"])
    user.organisation = org_b
    user.save(update_fields=["organisation"])

    detail_response = client.get(reverse("api_download_record_detail", args=[record_uuid]))
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["record"]
    assert detail_payload["file"]["authorized"] is False
    assert detail_payload["contributing_sources"] == []

    file_response = client.get(reverse("api_download_record_file", args=[record_uuid]))
    assert file_response.status_code == 403


def test_spatial_export_creates_download_record(client):
    layer = SpatialLayer.objects.create(
        layer_code="DL_LAYER",
        title="Download Layer",
        name="Download Layer",
        slug="download-layer",
        source_type=SpatialLayerSourceType.STATIC,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="F-1",
        name="Feature 1",
        geometry_json={
            "type": "Polygon",
            "coordinates": [[[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]],
        },
        properties_json={"province_code": "WC"},
    )

    response = client.get(reverse("api_spatial_layer_export_geojson", args=[layer.layer_code]))
    assert response.status_code == 200
    record = DownloadRecord.objects.filter(
        record_type=DownloadRecordType.SPATIAL_LAYER,
        object_uuid=layer.uuid,
    ).first()
    assert record is not None
    assert record.file_asset_path
    assert record.created_by is None


def test_report_export_creates_download_record(client):
    call_command("seed_mea_template_packs")
    org = Organisation.objects.create(name="Report Org", org_code="REPORT-ORG")
    user = User.objects.create_user(username="report_user", password="pass1234", organisation=org, is_staff=True)
    cycle = ReportingCycle.objects.create(
        code="REPORT-DL-CYCLE",
        title="Report Download Cycle",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        due_date=date(2026, 1, 31),
    )
    instance = ReportingInstance.objects.create(
        cycle=cycle,
        report_label="NR7",
        version_label="v1",
        focal_point_org=org,
        publishing_authority_org=org,
        created_by=user,
        status="submitted",
    )

    client.force_login(user)
    response = client.get(reverse("api_reporting_workspace_export_pdf", args=[instance.uuid]))
    assert response.status_code == 200

    record = DownloadRecord.objects.filter(
        record_type=DownloadRecordType.REPORT_EXPORT,
        object_uuid=instance.uuid,
    ).first()
    assert record is not None
    assert record.file_asset_path
    assert record.citation_text
