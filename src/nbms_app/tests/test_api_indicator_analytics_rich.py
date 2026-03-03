import json
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    Dataset,
    DatasetRelease,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorInputRequirement,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    Methodology,
    MethodologyStatus,
    MethodologyVersion,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
    User,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import ROLE_SECTION_LEAD


pytestmark = pytest.mark.django_db


def _seed_rich_indicator_stack():
    org = Organisation.objects.create(name="Analytics Org", org_code="ANL")
    target = NationalTarget.objects.create(
        code="T-AN",
        title="Threatened species target",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-RICH",
        title="Threatened species by family",
        national_target=target,
        organisation=org,
        indicator_type=NationalIndicatorType.HEADLINE,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        coverage_time_start_year=2022,
        coverage_time_end_year=2024,
        last_updated_on=date(2024, 12, 31),
        update_frequency="annual",
    )
    dataset = Dataset.objects.create(
        dataset_code="DS-RICH",
        title="Threatened species rollup",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    release_2022 = DatasetRelease.objects.create(
        dataset=dataset,
        version="2022.1",
        release_date=date(2022, 12, 31),
        snapshot_title="Threatened species 2022",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    release_2024 = DatasetRelease.objects.create(
        dataset=dataset,
        version="2024.1",
        release_date=date(2024, 12, 31),
        snapshot_title="Threatened species 2024",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    methodology = Methodology.objects.create(
        methodology_code="METH-RICH",
        title="Threatened species method",
        owner_org=org,
        is_active=True,
    )
    methodology_version = MethodologyVersion.objects.create(
        methodology=methodology,
        version="1.0",
        status=MethodologyStatus.ACTIVE,
        effective_date=date(2024, 1, 1),
        is_active=True,
        approval_body="ITSC approved",
    )
    IndicatorMethodologyVersionLink.objects.create(
        indicator=indicator,
        methodology_version=methodology_version,
        is_primary=True,
        is_active=True,
    )
    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Threatened species series",
        unit="species",
        value_type="numeric",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2022,
        value_numeric=Decimal("10.0"),
        dataset_release=release_2022,
        disaggregation={
            "province_code": "WC",
            "province_name": "Western Cape",
            "taxonomy_family": "Felidae",
            "threat_category": "EN",
        },
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2024,
        value_numeric=Decimal("12.0"),
        dataset_release=release_2024,
        uncertainty="expert review pending",
        disaggregation={
            "province_code": "WC",
            "province_name": "Western Cape",
            "taxonomy_family": "Felidae",
            "threat_category": "EN",
        },
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2024,
        value_numeric=Decimal("18.0"),
        dataset_release=release_2024,
        disaggregation={
            "province_code": "EC",
            "province_name": "Eastern Cape",
            "taxonomy_family": "Canidae",
            "threat_category": "CR",
        },
    )

    layer = SpatialLayer.objects.create(
        layer_code="ZA_PROVINCES_NE",
        title="Provinces",
        name="Provinces",
        slug="za-provinces-ne-rich",
        source_type=SpatialLayerSourceType.NBMS_TABLE,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_id="ZA-WC",
        feature_key="ZA-WC",
        province_code="WC",
        name="Western Cape",
        geometry_json={
            "type": "Polygon",
            "coordinates": [[[18.0, -34.0], [19.0, -34.0], [19.0, -33.0], [18.0, -33.0], [18.0, -34.0]]],
        },
        properties={"province_code": "WC"},
        properties_json={"province_code": "WC"},
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_id="ZA-EC",
        feature_key="ZA-EC",
        province_code="EC",
        name="Eastern Cape",
        geometry_json={
            "type": "Polygon",
            "coordinates": [[[25.0, -34.0], [26.0, -34.0], [26.0, -33.0], [25.0, -33.0], [25.0, -34.0]]],
        },
        properties={"province_code": "EC"},
        properties_json={"province_code": "EC"},
    )
    requirement = IndicatorInputRequirement.objects.create(indicator=indicator, cadence="annual")
    requirement.required_map_layers.add(layer)

    return {
        "org": org,
        "indicator": indicator,
        "series": series,
        "release_2022": release_2022,
        "release_2024": release_2024,
        "methodology_version": methodology_version,
        "layer": layer,
    }


def test_indicator_series_summary_honors_release_and_method_context(client):
    stack = _seed_rich_indicator_stack()
    response = client.get(
        reverse("api_indicator_series_summary", args=[stack["indicator"].uuid]),
        {
            "agg": "year",
            "release": str(stack["release_2022"].uuid),
            "method": "current",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert [row["bucket"] for row in payload["results"]] == [2022]
    assert payload["meta"]["release_used"]["uuid"] == str(stack["release_2022"].uuid)
    assert payload["meta"]["method_used"]["uuid"] == str(stack["methodology_version"].uuid)
    assert payload["meta"]["time_range"]["available_years"] == [2022]


def test_indicator_cube_dimensions_and_visual_profile_expose_taxonomy_and_categories(client):
    stack = _seed_rich_indicator_stack()

    cube_response = client.get(
        reverse("api_indicator_cube", args=[stack["indicator"].uuid]),
        {"group_by": "taxonomy_family,threat_category"},
    )
    assert cube_response.status_code == 200
    cube_payload = cube_response.json()
    assert any(
        row["taxonomy_family"] == "Felidae" and row["threat_category"] == "EN"
        for row in cube_payload["rows"]
    )

    dimensions_response = client.get(reverse("api_indicator_dimensions", args=[stack["indicator"].uuid]))
    assert dimensions_response.status_code == 200
    dimension_ids = {row["id"] for row in dimensions_response.json()["dimensions"]}
    assert {"province", "threat_category", "taxonomy_family"} <= dimension_ids

    global_dimensions = client.get(reverse("api_dimensions"))
    assert global_dimensions.status_code == 200
    assert any(row["id"] == "taxonomy_family" for row in global_dimensions.json()["dimensions"])

    profile_response = client.get(reverse("api_indicator_visual_profile", args=[stack["indicator"].uuid]))
    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert {"timeseries", "taxonomy", "distribution"} <= set(profile_payload["availableViews"])
    assert profile_payload["defaultView"] in {"taxonomy", "timeseries"}


def test_indicator_cube_honors_dimension_and_taxonomy_path_filters(client):
    stack = _seed_rich_indicator_stack()

    filtered_distribution = client.get(
        reverse("api_indicator_cube", args=[stack["indicator"].uuid]),
        {
            "group_by": "threat_category",
            "dim": "province",
            "dim_value": "WC",
        },
    )
    assert filtered_distribution.status_code == 200
    filtered_distribution_payload = filtered_distribution.json()
    assert filtered_distribution_payload["meta"]["applied_filters"]["dimension_filters"] == {"province": "WC"}
    assert filtered_distribution_payload["rows"] == [
        {
            "value": 12.0,
            "count": 1,
            "statusFlags": {
                "has_uncertainty": True,
                "has_release": True,
                "has_spatial": False,
            },
            "threat_category": "EN",
            "threat_category_label": "EN",
        }
    ]

    taxonomy_filtered = client.get(
        reverse("api_indicator_cube", args=[stack["indicator"].uuid]),
        {
            "group_by": "taxonomy_family,province",
            "tax_level": "family",
            "tax_code": "Felidae",
        },
    )
    assert taxonomy_filtered.status_code == 200
    taxonomy_filtered_payload = taxonomy_filtered.json()
    assert taxonomy_filtered_payload["meta"]["applied_filters"]["taxonomy_level"] == "family"
    assert taxonomy_filtered_payload["meta"]["applied_filters"]["taxonomy_path"] == ["Felidae"]
    assert all(row["taxonomy_family"] == "Felidae" for row in taxonomy_filtered_payload["rows"])


def test_indicator_map_supports_metric_selection_and_geo_filter(client):
    stack = _seed_rich_indicator_stack()
    response = client.get(
        reverse("api_indicator_map", args=[stack["indicator"].uuid]),
        {
            "year": 2024,
            "metric": "coverage",
            "geo_type": "province",
            "geo_code": "WC",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["selected_metric"] == "coverage"
    feature_lookup = {feature["properties"]["province_code"]: feature["properties"] for feature in payload["features"]}
    assert feature_lookup["WC"]["indicator_metric_value"] == 1
    assert feature_lookup["WC"]["indicator_selected"] is True
    assert feature_lookup["EC"]["indicator_metric_value"] is None


def test_indicator_audit_endpoint_returns_indicator_events(client):
    stack = _seed_rich_indicator_stack()
    actor = User.objects.create_user(username="audit-user", password="pass1234")
    record_audit_event(actor, "indicator_touch", stack["indicator"], metadata={"status": "published"})

    response = client.get(reverse("api_indicator_audit", args=[stack["indicator"].uuid]))
    assert response.status_code == 200
    payload = response.json()
    assert any(event["action"] == "indicator_touch" for event in payload["events"])


def test_governed_narrative_roundtrip_and_versions(client):
    stack = _seed_rich_indicator_stack()
    indicator = stack["indicator"]

    public_get = client.get(reverse("api_governed_narrative", args=["indicator", str(indicator.uuid)]))
    assert public_get.status_code == 200
    assert public_get.json()["narrative"]["can_edit"] is False

    editor = User.objects.create_user(username="narrative-editor", password="pass1234")
    group, _ = Group.objects.get_or_create(name=ROLE_SECTION_LEAD)
    editor.groups.add(group)
    client.force_login(editor)

    draft_payload = {
        "title": "Indicator interpretation",
        "sections": [
            {"id": "interpretation", "title": "Interpretation", "body": "## Overview\n\n**Stable** trajectory."},
            {"id": "key_messages", "title": "Key messages", "body": "- First finding"},
        ],
        "provenance_url": "https://example.org/methods/rich-indicator",
    }
    draft_response = client.post(
        reverse("api_governed_narrative_draft", args=["indicator", str(indicator.uuid)]),
        data=json.dumps(draft_payload),
        content_type="application/json",
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["narrative"]["status"] == "draft"
    assert draft_response.json()["narrative"]["sections"][0]["html"].startswith("<h2>Overview</h2>")

    submit_response = client.post(
        reverse("api_governed_narrative_submit", args=["indicator", str(indicator.uuid)]),
        data=json.dumps(draft_payload),
        content_type="application/json",
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["narrative"]["status"] == "pending_review"

    versions_response = client.get(reverse("api_governed_narrative_versions", args=["indicator", str(indicator.uuid)]))
    assert versions_response.status_code == 200
    versions = versions_response.json()["versions"]
    assert len(versions) >= 3
    assert versions[0]["status"] == "pending_review"
