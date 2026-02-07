import json

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from nbms_app.models import (
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorMethodProfile,
    IndicatorMethodType,
    IndicatorValueType,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    User,
)


pytestmark = pytest.mark.django_db


def _seed_indicator_with_method():
    org = Organisation.objects.create(name="Indicator Org", org_code="IND-ORG")
    target = NationalTarget.objects.create(
        code="T-METHOD",
        title="Target Method",
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    indicator = Indicator.objects.create(
        code="IND-METHOD-1",
        title="Indicator Method",
        national_target=target,
        indicator_type=NationalIndicatorType.OTHER,
        organisation=org,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    series = IndicatorDataSeries.objects.create(
        indicator=indicator,
        title="Series",
        unit="index",
        value_type=IndicatorValueType.NUMERIC,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
        organisation=org,
    )
    IndicatorDataPoint.objects.create(series=series, year=2021, value_numeric=10)
    IndicatorDataPoint.objects.create(series=series, year=2022, value_numeric=20)
    profile = IndicatorMethodProfile.objects.create(
        indicator=indicator,
        method_type=IndicatorMethodType.CSV_IMPORT,
        implementation_key="csv_import_aggregation",
        readiness_state="partial",
        is_active=True,
    )
    return indicator, profile


def test_indicator_methods_endpoint_returns_profiles(client):
    indicator, profile = _seed_indicator_with_method()
    response = client.get(reverse("api_indicator_methods", args=[indicator.uuid]))
    assert response.status_code == 200
    payload = response.json()
    assert payload["indicator_uuid"] == str(indicator.uuid)
    assert payload["profiles"][0]["uuid"] == str(profile.uuid)


def test_indicator_method_run_requires_editor_role(client):
    indicator, profile = _seed_indicator_with_method()
    org = indicator.organisation
    viewer = User.objects.create_user(username="viewer_method", password="pass12345", organisation=org)
    assert client.login(username="viewer_method", password="pass12345")
    response = client.post(
        reverse("api_indicator_method_run", args=[indicator.uuid, profile.uuid]),
        data=json.dumps({"params": {"foo": "bar"}}),
        content_type="application/json",
    )
    assert response.status_code == 403


def test_indicator_method_run_executes_for_indicator_lead(client, django_user_model):
    indicator, profile = _seed_indicator_with_method()
    user = django_user_model.objects.create_user(
        username="indicator_lead_user",
        password="pass12345",
        organisation=indicator.organisation,
    )
    group, _ = Group.objects.get_or_create(name="Indicator Lead")
    user.groups.add(group)
    assert client.login(username="indicator_lead_user", password="pass12345")

    response = client.post(
        reverse("api_indicator_method_run", args=[indicator.uuid, profile.uuid]),
        data=json.dumps({"params": {"window": 2}}),
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["output_json"]["method"] == "csv_import_aggregation"
