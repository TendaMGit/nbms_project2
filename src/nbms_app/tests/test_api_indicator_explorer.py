from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    Evidence,
    Framework,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    User,
)
from nbms_app.services.authorization import ROLE_SECRETARIAT


pytestmark = pytest.mark.django_db


def _seed_indicator_stack():
    org_a = Organisation.objects.create(name="Org A", org_code="ORG-A")
    org_b = Organisation.objects.create(name="Org B", org_code="ORG-B")

    target_a = NationalTarget.objects.create(
        code="T-A",
        title="Target A",
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
        title="Public indicator",
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

    return {
        "org_a": org_a,
        "org_b": org_b,
        "public": indicator_public,
        "hidden": indicator_hidden,
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
