from datetime import date
from decimal import Decimal

import pytest

from nbms_app.models import (
    EicatCategory,
    IASGoldSummary,
    Indicator,
    IndicatorDataPoint,
    IndicatorMethodProfile,
    IndicatorMethodType,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SeicatCategory,
    SensitivityLevel,
    TaxonGoldSummary,
    EcosystemGoldSummary,
)
from nbms_app.services.indicator_method_sdk import run_method_profile


pytestmark = pytest.mark.django_db


def _seed_indicator(code: str):
    org, _ = Organisation.objects.get_or_create(name="Registry Method Org", org_code="RMO")
    target, _ = NationalTarget.objects.get_or_create(
        code=f"NT-{code}",
        defaults={
            "title": f"Target {code}",
            "organisation": org,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
        },
    )
    indicator, _ = Indicator.objects.get_or_create(
        code=code,
        defaults={
            "title": f"Indicator {code}",
            "national_target": target,
            "indicator_type": NationalIndicatorType.OTHER,
            "organisation": org,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
        },
    )
    return indicator


def test_ecosystem_registry_method_generates_series_point():
    indicator = _seed_indicator("IND-ECO-METHOD")
    EcosystemGoldSummary.objects.create(
        snapshot_date=date(2026, 1, 31),
        dimension="province",
        dimension_key="WC",
        dimension_label="Western Cape",
        ecosystem_count=12,
        threatened_count=3,
        total_area_km2=Decimal("200.000"),
        protected_area_km2=Decimal("50.000"),
        protected_percent=Decimal("25.000"),
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    profile = IndicatorMethodProfile.objects.create(
        indicator=indicator,
        method_type=IndicatorMethodType.SCRIPTED_PYTHON,
        implementation_key="ecosystem_registry_summary",
        is_active=True,
    )
    run = run_method_profile(profile=profile, user=None, params={"year": 2026}, use_cache=False)
    assert run.status == "succeeded"
    point = IndicatorDataPoint.objects.filter(series__indicator=indicator, year=2026).first()
    assert point is not None
    assert point.value_numeric is not None


def test_ias_registry_method_generates_series_point():
    indicator = _seed_indicator("IND-IAS-METHOD")
    IASGoldSummary.objects.create(
        snapshot_date=date(2026, 1, 31),
        dimension="habitat",
        dimension_key="riparian",
        dimension_label="Riparian",
        eicat_category=EicatCategory.MR,
        seicat_category=SeicatCategory.MO,
        profile_count=10,
        invasive_count=6,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    profile = IndicatorMethodProfile.objects.create(
        indicator=indicator,
        method_type=IndicatorMethodType.SCRIPTED_PYTHON,
        implementation_key="ias_registry_pressure_index",
        is_active=True,
    )
    run = run_method_profile(profile=profile, user=None, params={"year": 2026}, use_cache=False)
    assert run.status == "succeeded"
    point = IndicatorDataPoint.objects.filter(series__indicator=indicator, year=2026).first()
    assert point is not None
    assert float(point.value_numeric) > 0


def test_taxon_registry_method_generates_series_point():
    indicator = _seed_indicator("IND-TAXON-METHOD")
    TaxonGoldSummary.objects.create(
        snapshot_date=date(2026, 1, 31),
        taxon_rank="species",
        is_native=True,
        is_endemic=False,
        has_voucher=True,
        is_ias=False,
        taxon_count=20,
        voucher_count=14,
        ias_profile_count=1,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    profile = IndicatorMethodProfile.objects.create(
        indicator=indicator,
        method_type=IndicatorMethodType.SCRIPTED_PYTHON,
        implementation_key="taxon_registry_native_voucher_ratio",
        is_active=True,
    )
    run = run_method_profile(profile=profile, user=None, params={"year": 2026}, use_cache=False)
    assert run.status == "succeeded"
    point = IndicatorDataPoint.objects.filter(series__indicator=indicator, year=2026).first()
    assert point is not None
    assert float(point.value_numeric) >= 0
