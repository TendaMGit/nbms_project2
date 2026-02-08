from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import connection, transaction
from django.db.models import Max
from django.utils import timezone

from nbms_app.models import (
    AlienTaxonProfile,
    EICATAssessment,
    EcosystemGoldDimension,
    EcosystemGoldSummary,
    EcosystemRiskAssessment,
    EcosystemType,
    EicatCategory,
    IASGoldDimension,
    IASGoldSummary,
    LifecycleStatus,
    SEICATAssessment,
    SeicatCategory,
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    TaxonConcept,
    TaxonGoldSummary,
)
from nbms_app.spatial_fields import GIS_ENABLED


THREAT_CATEGORIES = {"CR", "EN", "VU"}


def _pick_str(props: dict, keys):
    for key in keys:
        value = props.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def latest_snapshot_date(model) -> date | None:
    return model.objects.aggregate(value=Max("snapshot_date")).get("value")


def _coalesce_geom_sql(alias: str):
    return (
        f"COALESCE({alias}.geom, "
        f"CASE WHEN {alias}.geometry_json ? 'type' "
        f"THEN ST_SetSRID(ST_GeomFromGeoJSON({alias}.geometry_json::text), 4326) END)"
    )


def _refresh_taxon_gold(snapshot: date):
    TaxonGoldSummary.objects.filter(snapshot_date=snapshot).delete()
    ias_counts = defaultdict(int)
    for row in AlienTaxonProfile.objects.exclude(status=LifecycleStatus.ARCHIVED).values("taxon_id").annotate(total=Max("id")):
        ias_counts[row["taxon_id"]] += 1

    grouped = defaultdict(lambda: {"taxon_count": 0, "voucher_count": 0, "ias_profile_count": 0})
    queryset = TaxonConcept.objects.exclude(status=LifecycleStatus.ARCHIVED).order_by("id")
    for taxon in queryset:
        key = (
            taxon.organisation_id,
            taxon.taxon_rank or "",
            taxon.is_native,
            bool(taxon.is_endemic),
            bool(taxon.has_national_voucher_specimen),
            bool(ias_counts.get(taxon.id)),
        )
        grouped[key]["taxon_count"] += 1
        grouped[key]["voucher_count"] += int(taxon.voucher_specimen_count or 0)
        grouped[key]["ias_profile_count"] += int(ias_counts.get(taxon.id, 0))

    rows = []
    for key, values in grouped.items():
        (
            organisation_id,
            taxon_rank,
            is_native,
            is_endemic,
            has_voucher,
            is_ias,
        ) = key
        rows.append(
            TaxonGoldSummary(
                snapshot_date=snapshot,
                organisation_id=organisation_id,
                taxon_rank=taxon_rank,
                is_native=is_native,
                is_endemic=is_endemic,
                has_voucher=has_voucher,
                is_ias=is_ias,
                taxon_count=values["taxon_count"],
                voucher_count=values["voucher_count"],
                ias_profile_count=values["ias_profile_count"],
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.PUBLIC,
                source_system="registry_marts",
                source_ref="taxon_gold_v1",
            )
        )
    TaxonGoldSummary.objects.bulk_create(rows, batch_size=500)
    return len(rows)


def _ecosystem_area_by_dimension(layer, property_keys):
    if not layer or not GIS_ENABLED:
        return {}
    geom_sql = _coalesce_geom_sql("sf")
    key_sql = "COALESCE(NULLIF(" + "COALESCE(" + ",".join(
        [f"sf.properties->>'{key}'" for key in property_keys]
        + [f"sf.properties_json->>'{key}'" for key in property_keys]
    ) + "), ''), 'Unknown')"
    query = f"""
        SELECT
            {key_sql} AS bucket,
            ROUND(SUM(ST_Area({geom_sql}::geography) / 1000000.0)::numeric, 6) AS area_km2
        FROM nbms_app_spatialfeature sf
        WHERE sf.layer_id = %s AND {geom_sql} IS NOT NULL
        GROUP BY bucket
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [layer.id])
        return {str(bucket): Decimal(str(area or 0)) for bucket, area in cursor.fetchall()}


def _province_protected_rows():
    admin = SpatialLayer.objects.filter(layer_code__in=["ZA_PROVINCES_NE", "ZA_PROVINCES"], is_active=True).order_by("id").first()
    protected = SpatialLayer.objects.filter(
        layer_code__in=["ZA_PROTECTED_AREAS_NE", "ZA_PROTECTED_AREAS"],
        is_active=True,
    ).order_by("id").first()
    if not admin or not protected or not GIS_ENABLED:
        return []
    query = f"""
        WITH admin AS (
            SELECT
                COALESCE(NULLIF(sf.province_code, ''), sf.feature_key, sf.feature_id, 'UNKNOWN') AS province_code,
                COALESCE(NULLIF(sf.name, ''), sf.feature_key, sf.feature_id, 'Unknown') AS province_name,
                {_coalesce_geom_sql("sf")} AS geom
            FROM nbms_app_spatialfeature sf
            WHERE sf.layer_id = %s
        ),
        protected AS (
            SELECT ST_UnaryUnion(ST_Collect({_coalesce_geom_sql("sf")})) AS geom
            FROM nbms_app_spatialfeature sf
            WHERE sf.layer_id = %s
        )
        SELECT
            a.province_code,
            a.province_name,
            ROUND((ST_Area(a.geom::geography) / 1000000.0)::numeric, 6) AS province_area_km2,
            ROUND(
                (CASE WHEN p.geom IS NULL THEN 0
                      ELSE ST_Area(ST_Intersection(a.geom, p.geom)::geography) / 1000000.0
                 END)::numeric,
                6
            ) AS protected_area_km2
        FROM admin a
        CROSS JOIN protected p
        WHERE a.geom IS NOT NULL
        ORDER BY a.province_code
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [admin.id, protected.id])
        rows = []
        for code, name, total_km2, protected_km2 in cursor.fetchall():
            total = Decimal(str(total_km2 or 0))
            protected_area = Decimal(str(protected_km2 or 0))
            pct = Decimal("0")
            if total > 0:
                pct = (protected_area / total) * Decimal("100")
            rows.append(
                {
                    "province_code": str(code or "UNKNOWN"),
                    "province_name": str(name or "Unknown"),
                    "total_area_km2": total.quantize(Decimal("0.001")),
                    "protected_area_km2": protected_area.quantize(Decimal("0.001")),
                    "protected_percent": pct.quantize(Decimal("0.001")),
                }
            )
        return rows


def _refresh_ecosystem_gold(snapshot: date):
    EcosystemGoldSummary.objects.filter(snapshot_date=snapshot).delete()
    ecosystems = list(EcosystemType.objects.exclude(status=LifecycleStatus.ARCHIVED).order_by("id"))
    latest_assessments = {}
    for row in EcosystemRiskAssessment.objects.order_by("ecosystem_type_id", "-assessment_year", "-id"):
        if row.ecosystem_type_id not in latest_assessments:
            latest_assessments[row.ecosystem_type_id] = row

    eco_layer = SpatialLayer.objects.filter(layer_code__in=["ZA_ECOSYSTEM_PROXY_NE"], is_active=True).order_by("id").first()
    biome_area = _ecosystem_area_by_dimension(eco_layer, ["BIOME", "biome", "BIOME_NAME"])
    bioregion_area = _ecosystem_area_by_dimension(eco_layer, ["BIOREGION", "bioregion", "ECO_REGION"])

    grouped = defaultdict(lambda: {"ecosystem_count": 0, "threatened_count": 0})
    threat_grouped = defaultdict(int)
    for ecosystem in ecosystems:
        threat_category = ""
        latest = latest_assessments.get(ecosystem.id)
        if latest:
            threat_category = (latest.category or "").upper()
        for dim, value in [
            (EcosystemGoldDimension.BIOME, ecosystem.biome or "Unknown"),
            (EcosystemGoldDimension.BIOREGION, ecosystem.bioregion or "Unknown"),
        ]:
            key = (ecosystem.organisation_id, dim, str(value))
            grouped[key]["ecosystem_count"] += 1
            if threat_category in THREAT_CATEGORIES:
                grouped[key]["threatened_count"] += 1
        if threat_category:
            threat_grouped[(ecosystem.organisation_id, threat_category)] += 1

    rows = []
    for key, counts in grouped.items():
        org_id, dim, value = key
        total_area = Decimal("0")
        if dim == EcosystemGoldDimension.BIOME:
            total_area = biome_area.get(value, Decimal("0"))
        elif dim == EcosystemGoldDimension.BIOREGION:
            total_area = bioregion_area.get(value, Decimal("0"))
        rows.append(
            EcosystemGoldSummary(
                snapshot_date=snapshot,
                organisation_id=org_id,
                dimension=dim,
                dimension_key=value,
                dimension_label=value,
                ecosystem_count=counts["ecosystem_count"],
                threatened_count=counts["threatened_count"],
                total_area_km2=total_area,
                protected_area_km2=Decimal("0"),
                protected_percent=Decimal("0"),
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.PUBLIC,
                source_system="registry_marts",
                source_ref="ecosystem_gold_v1",
            )
        )

    for key, value in threat_grouped.items():
        org_id, threat_category = key
        rows.append(
            EcosystemGoldSummary(
                snapshot_date=snapshot,
                organisation_id=org_id,
                dimension=EcosystemGoldDimension.THREAT_CATEGORY,
                dimension_key=threat_category,
                dimension_label=threat_category,
                ecosystem_count=value,
                threatened_count=value if threat_category in THREAT_CATEGORIES else 0,
                total_area_km2=Decimal("0"),
                protected_area_km2=Decimal("0"),
                protected_percent=Decimal("0"),
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.PUBLIC,
                source_system="registry_marts",
                source_ref="ecosystem_gold_v1",
            )
        )

    for row in _province_protected_rows():
        rows.append(
            EcosystemGoldSummary(
                snapshot_date=snapshot,
                dimension=EcosystemGoldDimension.PROVINCE,
                dimension_key=row["province_code"],
                dimension_label=row["province_name"],
                ecosystem_count=0,
                threatened_count=0,
                total_area_km2=row["total_area_km2"],
                protected_area_km2=row["protected_area_km2"],
                protected_percent=row["protected_percent"],
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.PUBLIC,
                source_system="registry_marts",
                source_ref="ecosystem_gold_v1",
            )
        )

    EcosystemGoldSummary.objects.bulk_create(rows, batch_size=500)
    return len(rows)


def _latest_category_map(model_cls, fk_field):
    latest = {}
    for row in model_cls.objects.order_by(fk_field, "-assessed_on", "-id"):
        key = getattr(row, fk_field)
        if key and key not in latest:
            latest[key] = row.category
    return latest


def _refresh_ias_gold(snapshot: date):
    IASGoldSummary.objects.filter(snapshot_date=snapshot).delete()
    profiles = list(AlienTaxonProfile.objects.exclude(status=LifecycleStatus.ARCHIVED).order_by("id"))
    latest_eicat = _latest_category_map(EICATAssessment, "profile_id")
    latest_seicat = _latest_category_map(SEICATAssessment, "profile_id")

    grouped = defaultdict(lambda: {"profile_count": 0, "invasive_count": 0})
    for profile in profiles:
        habitats = profile.habitat_types_json if isinstance(profile.habitat_types_json, list) else []
        habitats = [str(item).strip() for item in habitats if str(item).strip()] or ["unknown"]
        pathway = profile.pathway_code or "unknown"
        eicat = latest_eicat.get(profile.id, EicatCategory.NE)
        seicat = latest_seicat.get(profile.id, SeicatCategory.NE)

        for habitat in habitats:
            key = (
                profile.organisation_id,
                IASGoldDimension.HABITAT,
                habitat.lower(),
                habitat,
                eicat,
                seicat,
            )
            grouped[key]["profile_count"] += 1
            grouped[key]["invasive_count"] += int(profile.is_invasive)

        system_key = (
            profile.organisation_id,
            IASGoldDimension.SYSTEM,
            pathway,
            pathway.replace("_", " "),
            eicat,
            seicat,
        )
        grouped[system_key]["profile_count"] += 1
        grouped[system_key]["invasive_count"] += int(profile.is_invasive)

    rows = []
    for key, values in grouped.items():
        org_id, dim, dim_key, dim_label, eicat, seicat = key
        rows.append(
            IASGoldSummary(
                snapshot_date=snapshot,
                organisation_id=org_id,
                dimension=dim,
                dimension_key=dim_key,
                dimension_label=dim_label,
                eicat_category=eicat,
                seicat_category=seicat,
                profile_count=values["profile_count"],
                invasive_count=values["invasive_count"],
                status=LifecycleStatus.PUBLISHED,
                sensitivity=SensitivityLevel.PUBLIC,
                source_system="registry_marts",
                source_ref="ias_gold_v1",
            )
        )
    IASGoldSummary.objects.bulk_create(rows, batch_size=500)
    return len(rows)


@transaction.atomic
def refresh_registry_gold_marts(*, snapshot_date: date | None = None):
    snapshot = snapshot_date or timezone.now().date()
    return {
        "snapshot_date": snapshot.isoformat(),
        "taxon_rows": _refresh_taxon_gold(snapshot),
        "ecosystem_rows": _refresh_ecosystem_gold(snapshot),
        "ias_rows": _refresh_ias_gold(snapshot),
    }
