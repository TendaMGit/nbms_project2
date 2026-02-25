from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    Dataset,
    Evidence,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorInputRequirement,
    IndicatorRegistryCoverageRequirement,
    LifecycleStatus,
    MonitoringProgramme,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    ProgrammeTemplate,
    ProgrammeTemplateDomain,
    ReportProductTemplate,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialLayerSourceType,
    SpatialSource,
    SpatialSourceFormat,
    User,
)
from nbms_app.services.authorization import ROLE_SECRETARIAT


pytestmark = pytest.mark.django_db


def _seed_indicator_stack():
    org_a = Organisation.objects.create(name="Org A", org_code="ORG-A")
    org_b = Organisation.objects.create(name="Org B", org_code="ORG-B")

    target_a = NationalTarget.objects.create(
        code="T-A",
        title="Forest Target A",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    target_b = NationalTarget.objects.create(
        code="T-B",
        title="Target B",
        organisation=org_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    indicator_public = Indicator.objects.create(
        code="IND-PUB",
        title="Forest indicator",
        national_target=target_a,
        organisation=org_a,
        indicator_type=NationalIndicatorType.OTHER,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        coverage_time_start_year=2018,
        coverage_time_end_year=2022,
        coverage_geography="South Africa",
    )
    indicator_hidden = Indicator.objects.create(
        code="IND-HIDDEN",
        title="Hidden indicator",
        national_target=target_b,
        organisation=org_b,
        indicator_type=NationalIndicatorType.OTHER,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.RESTRICTED,
    )

    framework = Framework.objects.create(
        code="GBF",
        title="GBF",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org_a,
    )
    fw_target = FrameworkTarget.objects.create(
        framework=framework,
        code="1",
        title="Target 1",
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org_a,
    )
    fw_indicator = FrameworkIndicator.objects.create(
        framework=framework,
        framework_target=fw_target,
        code="GBF-H1",
        title="Headline 1",
        indicator_type=FrameworkIndicatorType.HEADLINE,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org_a,
    )
    IndicatorFrameworkIndicatorLink.objects.create(
        indicator=indicator_public,
        framework_indicator=fw_indicator,
        relation_type="supporting",
        is_active=True,
    )

    series = IndicatorDataSeries.objects.create(
        indicator=indicator_public,
        title="Series A",
        unit="index",
        value_type="numeric",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2021,
        value_numeric=Decimal("10.0"),
        disaggregation={"province": "ALL"},
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2022,
        value_numeric=Decimal("12.0"),
        disaggregation={"province": "ALL"},
    )

    dataset_public = Dataset.objects.create(
        dataset_code="DS-FOREST",
        title="Forest Monitoring Dataset",
        description="Forest baseline release",
        organisation=org_a,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    IndicatorDatasetLink.objects.create(indicator=indicator_public, dataset=dataset_public, note="primary")
    dataset_hidden = Dataset.objects.create(
        dataset_code="DS-HIDDEN",
        title="Hidden Restricted Dataset",
        description="Restricted source payload",
        organisation=org_b,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.RESTRICTED,
    )
    IndicatorDatasetLink.objects.create(indicator=indicator_hidden, dataset=dataset_hidden, note="restricted")

    return {
        "org_a": org_a,
        "org_b": org_b,
        "public": indicator_public,
        "hidden": indicator_hidden,
        "dataset_public": dataset_public,
        "dataset_hidden": dataset_hidden,
    }


def test_indicator_list_abac_for_anonymous(client):
    stack = _seed_indicator_stack()
    response = client.get(reverse("api_indicator_list"))
    assert response.status_code == 200
    payload = response.json()
    codes = [row["code"] for row in payload["results"]]
    assert stack["public"].code in codes
    assert stack["hidden"].code not in codes
    public_row = next(row for row in payload["results"] if row["code"] == stack["public"].code)
    assert public_row["method_readiness_state"] == "blocked"
    assert public_row["method_types"] == []


def test_indicator_list_framework_filter(client):
    _seed_indicator_stack()
    response = client.get(reverse("api_indicator_list"), {"framework": "GBF"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["code"] == "IND-PUB"


def test_indicator_detail_returns_404_for_hidden_indicator(client):
    stack = _seed_indicator_stack()
    response = client.get(reverse("api_indicator_detail", args=[stack["hidden"].uuid]))
    assert response.status_code == 404


def test_discovery_search_returns_indicator_target_and_dataset(client):
    stack = _seed_indicator_stack()
    response = client.get(reverse("api_discovery_search"), {"search": "forest"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["indicators"] >= 1
    assert payload["counts"]["targets"] >= 1
    assert payload["counts"]["datasets"] >= 1
    indicator_codes = {row["code"] for row in payload["indicators"]}
    target_codes = {row["code"] for row in payload["targets"]}
    dataset_codes = {row["code"] for row in payload["datasets"]}
    assert stack["public"].code in indicator_codes
    assert "T-A" in target_codes
    assert stack["dataset_public"].dataset_code in dataset_codes


def test_discovery_search_hides_restricted_records_for_anonymous(client):
    _seed_indicator_stack()
    response = client.get(reverse("api_discovery_search"), {"search": "hidden"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"] == {"indicators": 0, "targets": 0, "datasets": 0}
    assert payload["indicators"] == []
    assert payload["targets"] == []
    assert payload["datasets"] == []


def test_indicator_series_summary_returns_grouped_values(client):
    stack = _seed_indicator_stack()
    response = client.get(
        reverse("api_indicator_series_summary", args=[stack["public"].uuid]),
        {"agg": "year"},
    )
    assert response.status_code == 200
    payload = response.json()
    buckets = [row["bucket"] for row in payload["results"]]
    assert buckets == [2021, 2022]


def test_indicator_series_summary_supports_province_aggregation(client):
    stack = _seed_indicator_stack()
    series = IndicatorDataSeries.objects.get(indicator=stack["public"])
    IndicatorDataPoint.objects.create(
        series=series,
        year=2023,
        value_numeric=Decimal("18.0"),
        disaggregation={"province_code": "WC", "province_name": "Western Cape"},
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2023,
        value_numeric=Decimal("24.0"),
        disaggregation={"province_code": "EC", "province_name": "Eastern Cape"},
    )
    response = client.get(
        reverse("api_indicator_series_summary", args=[stack["public"].uuid]),
        {"agg": "province"},
    )
    assert response.status_code == 200
    payload = response.json()
    buckets = [row["bucket"] for row in payload["results"]]
    assert "WC" in buckets
    assert "EC" in buckets


def test_indicator_map_returns_admin_features_with_indicator_values(client):
    stack = _seed_indicator_stack()
    indicator = stack["public"]
    series = IndicatorDataSeries.objects.get(indicator=indicator)
    IndicatorDataPoint.objects.create(
        series=series,
        year=2024,
        value_numeric=Decimal("19.4"),
        disaggregation={"province_code": "WC", "province_name": "Western Cape"},
    )
    IndicatorDataPoint.objects.create(
        series=series,
        year=2024,
        value_numeric=Decimal("31.2"),
        disaggregation={"province_code": "EC", "province_name": "Eastern Cape"},
    )

    layer = SpatialLayer.objects.create(
        layer_code="ZA_PROVINCES_NE",
        title="Provinces",
        name="Provinces",
        slug="za-provinces-ne",
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

    response = client.get(
        reverse("api_indicator_map", args=[indicator.uuid]),
        {"year": 2024},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    values = {feature["properties"]["province_code"]: feature["properties"]["indicator_value"] for feature in payload["features"]}
    assert values["WC"] == pytest.approx(19.4)
    assert values["EC"] == pytest.approx(31.2)


def test_indicator_publish_transition_requires_evidence(client):
    stack = _seed_indicator_stack()
    org = stack["org_a"]
    indicator = stack["public"]
    indicator.status = LifecycleStatus.APPROVED
    indicator.save(update_fields=["status"])

    user = User.objects.create_user(
        username="publisher",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=ROLE_SECRETARIAT)
    user.groups.add(group)
    client.force_login(user)

    response = client.post(
        reverse("api_indicator_transition", args=[indicator.uuid]),
        {"action": "publish"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Evidence is required" in response.json()["detail"]

    evidence = Evidence.objects.create(
        title="Evidence",
        evidence_type="report",
        source_url="https://example.org/evidence",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    IndicatorEvidenceLink.objects.create(indicator=indicator, evidence=evidence, note="required")

    response = client.post(
        reverse("api_indicator_transition", args=[indicator.uuid]),
        {"action": "publish"},
        content_type="application/json",
    )
    assert response.status_code == 200
    indicator.refresh_from_db()
    assert indicator.status == LifecycleStatus.PUBLISHED


def test_indicator_detail_includes_spatial_readiness_panel_data(client):
    stack = _seed_indicator_stack()
    indicator = stack["public"]
    layer = SpatialLayer.objects.create(
        layer_code="ZA_PROVINCES_NE",
        title="Provinces",
        name="Provinces",
        slug="za-provinces-ne",
        source_type=SpatialLayerSourceType.NBMS_TABLE,
        sensitivity=SensitivityLevel.PUBLIC,
        is_public=True,
        is_active=True,
    )
    source = SpatialSource.objects.create(
        code="NE_ADMIN1_ZA",
        title="Natural Earth admin1",
        source_url="https://example.org/admin1.zip",
        source_format=SpatialSourceFormat.ZIP_SHAPEFILE,
        source_type=SpatialLayerSourceType.UPLOADED_FILE,
        layer_code="ZA_PROVINCES_NE",
        layer_title="Provinces",
        layer_description="",
        sensitivity=SensitivityLevel.PUBLIC,
        last_status="ready",
        last_feature_count=9,
    )
    requirement = IndicatorInputRequirement.objects.create(indicator=indicator, cadence="annual")
    requirement.required_map_layers.add(layer)
    requirement.required_map_sources.add(source)

    response = client.get(reverse("api_indicator_detail", args=[indicator.uuid]))
    assert response.status_code == 200
    payload = response.json()
    readiness = payload["spatial_readiness"]
    assert readiness["overall_ready"] is True
    assert readiness["layer_requirements"][0]["layer_code"] == "ZA_PROVINCES_NE"
    assert readiness["source_requirements"][0]["code"] == "NE_ADMIN1_ZA"


def test_indicator_detail_includes_registry_readiness_and_used_by_graph(client):
    stack = _seed_indicator_stack()
    indicator = stack["public"]
    org = stack["org_a"]
    user = User.objects.create_user(
        username="indicator-user",
        password="pass1234",
        organisation=org,
        is_staff=True,
    )
    client.force_login(user)
    IndicatorRegistryCoverageRequirement.objects.create(
        indicator=indicator,
        require_ecosystem_registry=True,
        require_taxon_registry=True,
        require_ias_registry=False,
        min_ecosystem_count=2,
        min_taxon_count=1,
    )
    MonitoringProgramme.objects.create(
        programme_code="NBMS-PROG-TAXA",
        title="Taxa Programme",
        programme_type="national",
        lead_org=org,
        is_active=True,
    ).indicator_links.create(
        indicator=indicator,
        relationship_type="supporting",
        role="readiness",
        is_active=True,
    )
    ProgrammeTemplate.objects.create(
        template_code="NBMS-PROG-TAXA",
        title="Taxa Template",
        domain=ProgrammeTemplateDomain.TAXA,
        pipeline_definition_json={"steps": []},
        required_outputs_json=[],
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    ReportProductTemplate.objects.create(
        code="nba_v1",
        title="NBA",
        version="v1",
        description="NBA shell",
        schema_json={"sections": ["A", "B"]},
        export_handler="nba_v1",
        is_active=True,
    )

    response = client.get(reverse("api_indicator_detail", args=[indicator.uuid]))
    assert response.status_code == 200
    payload = response.json()
    assert "registry_readiness" in payload
    assert payload["registry_readiness"]["overall_ready"] is False
    assert payload["used_by_graph"]["programmes"][0]["programme_code"] == "NBMS-PROG-TAXA"
    assert payload["used_by_graph"]["report_products"]
