from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from nbms_app.models import (
    AlignmentRelationType,
    Dataset,
    DatasetRelease,
    Evidence,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorDataPoint,
    IndicatorDataSeries,
    IndicatorDatasetLink,
    IndicatorEvidenceLink,
    IndicatorFrameworkIndicatorLink,
    IndicatorMethodProfile,
    IndicatorMethodReadiness,
    IndicatorMethodType,
    IndicatorMethodologyVersionLink,
    IndicatorReportingCapability,
    IndicatorValueType,
    License,
    LifecycleStatus,
    Methodology,
    MethodologyIndicatorLink,
    MethodologyStatus,
    MethodologyVersion,
    NationalIndicatorType,
    NationalTarget,
    NationalTargetFrameworkTargetLink,
    Organisation,
    QaStatus,
    RelationshipType,
    SensitivityLevel,
    UpdateFrequency,
)


PILOT_ROOT = Path(__file__).resolve().parents[1] / "pilots"
DEFAULT_MANIFEST_PATH = PILOT_ROOT / "nba_pilot_v1.yml"

BIOME_CODE_MAP = {
    "Albany Thicket": "THI",
    "Azonal": "AZO",
    "Desert": "DES",
    "Forest": "FOR",
    "Fynbos": "FYN",
    "Grassland": "GRA",
    "Indian Ocean Coastal Belt": "IOC",
    "Nama Karoo": "NAK",
    "Savanna": "SAV",
    "Succulent Karoo": "SUK",
}

RLE_LABELS = {
    "CR": "Critically endangered",
    "EN": "Endangered",
    "VU": "Vulnerable",
    "NT": "Near threatened",
    "LC": "Least concern",
}

EPL_LABELS = {
    "WP": "Well protected",
    "MP": "Moderately protected",
    "PP": "Poorly protected",
    "NP": "Not protected",
}

GBF_GOALS = {
    "A": "The integrity, connectivity and resilience of ecosystems are maintained, enhanced, or restored.",
    "B": "Biodiversity is sustainably used and managed and nature's contributions to people are maintained.",
    "D": "The means of implementation for biodiversity action are enabled and integrated into decision-making.",
}

GBF_TARGETS = {
    "2": ("A", "Restore, maintain and enhance ecosystems and reduce collapse risk."),
    "3": ("A", "Conserve and effectively manage protected and conserved areas."),
    "4": ("A", "Halt human-induced extinction and recover species."),
    "6": ("B", "Reduce impacts of invasive alien species."),
    "14": ("D", "Integrate biodiversity values into policy and planning."),
    "17": ("D", "Strengthen biosafety and biotechnology risk management."),
    "21": ("D", "Ensure data, information and knowledge are available for decision-making."),
}

SECONDARY_FRAMEWORKS = {
    "SDG": {
        "title": "Sustainable Development Goals",
        "targets": {
            "15": "Life on land",
        },
    },
    "RAMSAR": {
        "title": "Ramsar Convention",
        "targets": {
            "PILOT-1": "Pilot wetland and ecosystem reporting linkage pending review",
        },
    },
    "CITES": {
        "title": "Convention on International Trade in Endangered Species",
        "targets": {
            "PILOT-1": "Pilot species trade and protection linkage pending review",
        },
    },
    "CMS": {
        "title": "Convention on Migratory Species",
        "targets": {
            "PILOT-1": "Pilot migratory species linkage pending review",
        },
    },
}


class PilotIngestError(Exception):
    pass


@dataclass(frozen=True)
class ParsedIndicatorPayload:
    title: str
    unit: str
    value_type: str
    methodology: str
    source_notes: str
    disaggregation_schema: dict[str, Any]
    points: list[dict[str, Any]]
    coverage_geography: str
    coverage_time_start_year: int | None
    coverage_time_end_year: int | None


def load_manifest(manifest_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(manifest_path or DEFAULT_MANIFEST_PATH)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not isinstance(data.get("indicators"), list):
        raise PilotIngestError("Manifest must define an 'indicators' list.")
    data["_manifest_path"] = str(path)
    return data


def ingest_manifest(*, manifest_path: str | Path | None = None, stdout=None) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    report = {
        "manifest_version": manifest.get("version") or "unknown",
        "manifest_path": manifest.get("_manifest_path"),
        "started_at": timezone.now().isoformat(),
        "entries": [],
        "errors": [],
    }
    for entry in manifest["indicators"]:
        try:
            with transaction.atomic():
                entry_report = ingest_manifest_entry(manifest=manifest, entry=entry)
                report["entries"].append(entry_report)
                if stdout:
                    stdout.write(
                        f"[pilot] {entry_report['indicator_code']}: "
                        f"dataset={entry_report['dataset_code']} release={entry_report['release_version']} "
                        f"points={entry_report['points_written']}"
                    )
        except Exception as exc:  # noqa: BLE001
            error_payload = {
                "indicator_code": entry.get("indicator_code"),
                "error": str(exc),
            }
            report["errors"].append(error_payload)
            if stdout:
                stdout.write(f"[pilot] {entry.get('indicator_code')}: FAILED {exc}")
    report["finished_at"] = timezone.now().isoformat()
    report["success"] = not report["errors"]
    return report


def ingest_manifest_entry(*, manifest: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    manifest_path = Path(str(manifest["_manifest_path"]))
    organisation = _ensure_organisation(
        code=str(entry["dataset_metadata"].get("owner_org_code") or "SANBI"),
        name=str(entry["dataset_metadata"].get("owner_org") or "SANBI"),
    )
    license_obj = _ensure_license(entry["dataset_metadata"])
    asset_manifest = _store_bronze_assets(manifest_path.parent, entry)
    csv_rows = _load_csv_rows(manifest_path.parent, entry)
    parsed = _parse_entry(entry, csv_rows)
    release_date = _parse_iso_date(entry.get("repo_ref_date"))

    dataset = _upsert_dataset(entry=entry, organisation=organisation, license_obj=license_obj)
    dataset_release = _upsert_dataset_release(
        entry=entry,
        dataset=dataset,
        organisation=organisation,
        release_date=release_date,
        asset_manifest=asset_manifest,
        manifest_version=str(manifest.get("version") or "unknown"),
    )
    indicator = _upsert_indicator(entry=entry, organisation=organisation, release_date=release_date, parsed=parsed)
    _link_dataset(entry=entry, indicator=indicator, dataset=dataset)
    _upsert_methodology(entry=entry, indicator=indicator, organisation=organisation, release_date=release_date)
    _upsert_method_profile(indicator=indicator, entry=entry, parsed=parsed)
    evidence_codes = _upsert_evidence(entry=entry, indicator=indicator, organisation=organisation)
    _upsert_series_and_points(
        indicator=indicator,
        dataset_release=dataset_release,
        organisation=organisation,
        parsed=parsed,
        entry=entry,
    )
    mapping_report = _upsert_mea_mappings(entry=entry, indicator=indicator, organisation=organisation)
    return {
        "indicator_code": indicator.code,
        "dataset_code": dataset.dataset_code,
        "release_version": dataset_release.version,
        "release_date": dataset_release.release_date.isoformat() if dataset_release.release_date else None,
        "points_written": len(parsed.points),
        "pack_id": indicator.visual_pack_id,
        "evidence_codes": evidence_codes,
        "framework_mappings": mapping_report,
    }


def _store_bronze_assets(manifest_dir: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    asset_manifest: list[dict[str, Any]] = []
    for file_spec in entry.get("files", []):
        vendored_path = manifest_dir / str(file_spec["vendored_path"])
        content = vendored_path.read_bytes()
        relative_name = str(file_spec["path"]).replace("\\", "/").split("/")[-1]
        storage_path = (
            f"pilots/{slugify(str(entry['indicator_code']).lower())}/"
            f"{str(entry['repo_ref'])[:12]}/{relative_name}"
        )
        if default_storage.exists(storage_path):
            default_storage.delete(storage_path)
        default_storage.save(storage_path, ContentFile(content))
        asset_manifest.append(
            {
                "alias": file_spec.get("alias"),
                "path": file_spec.get("path"),
                "vendored_path": file_spec.get("vendored_path"),
                "kind": file_spec.get("kind"),
                "storage_path": storage_path,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return asset_manifest


def _load_csv_rows(manifest_dir: Path, entry: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    rows_by_alias: dict[str, list[dict[str, str]]] = {}
    for file_spec in entry.get("files", []):
        vendored_path = manifest_dir / str(file_spec["vendored_path"])
        if vendored_path.suffix.lower() != ".csv":
            continue
        with vendored_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows_by_alias[str(file_spec["alias"])] = [dict(row) for row in reader]
    return rows_by_alias


def _parse_entry(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    parser = str(entry.get("parser") or "").strip().lower()
    if parser == "rle_terr":
        return _parse_rle_terr(entry, csv_rows)
    if parser == "rle_terr_matrix":
        return _parse_rle_terr_matrix(entry, csv_rows)
    if parser == "epl_terr":
        return _parse_epl_terr(entry, csv_rows)
    if parser == "rle_est":
        return _parse_rle_est(entry, csv_rows)
    if parser == "rle_est_matrix":
        return _parse_rle_est_matrix(entry, csv_rows)
    if parser == "tepi_terr":
        return _parse_tepi_terr(entry, csv_rows)
    if parser == "plant_spi_demo":
        return _parse_plant_spi_demo(entry, csv_rows)
    raise PilotIngestError(f"Unsupported pilot parser '{parser}'.")


def _parse_rle_terr(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    required = {"results_a3", "compiled_adjusted", "integration"}
    _require_aliases(entry, csv_rows, required)
    integration_lookup = {str(row.get("type") or "").strip(): row for row in csv_rows["integration"]}
    compiled_lookup = {str(row.get("T_MAPCODE") or "").strip(): row for row in csv_rows["compiled_adjusted"]}
    points: list[dict[str, Any]] = []
    for row in csv_rows["results_a3"]:
        type_code = str(row.get("T_MAPCODE") or "").strip()
        if not type_code:
            continue
        integration = integration_lookup.get(type_code, {})
        compiled = compiled_lookup.get(type_code, {})
        zone = str(integration.get("zone") or "").strip() or "Unknown"
        get_code = str(integration.get("get") or "").strip()
        for year in ("1990", "2014", "2018", "2020", "2022"):
            value = _decimal(row.get(year))
            if value is None:
                continue
            rle_category = str(row.get(f"A3_{year}") or compiled.get("RLE") or integration.get("RLE") or "").strip()
            epl_category = str(integration.get("EPL") or "").strip()
            points.append(
                {
                    "year": int(year),
                    "value_numeric": value,
                    "disaggregation": {
                        **_ecosystem_disaggregation(
                            ecosystem_code=type_code,
                            ecosystem_label=type_code,
                            biome_name=zone,
                            realm_name="Terrestrial",
                            get_code=get_code,
                        ),
                        **_rle_category_payload(rle_category),
                        **_epl_category_payload(epl_category),
                        "rle_matrix_bucket": str(integration.get("RLE_EPL") or "").strip(),
                        "criterion_a2b_category": str(compiled.get("A2b_fin") or "").strip(),
                    },
                }
            )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from terrestrial RLE workflow outputs with annual area estimates and current RLE/EPL classifications.",
        coverage_geography="National by biome and ecosystem type",
    )


def _parse_rle_terr_matrix(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    _require_aliases(entry, csv_rows, {"integration"})
    points = []
    for row in csv_rows["integration"]:
        type_code = str(row.get("type") or "").strip()
        if not type_code:
            continue
        points.append(
            {
                "year": 2022,
                "value_numeric": _decimal(row.get("extent")) or Decimal("0"),
                "disaggregation": {
                    **_ecosystem_disaggregation(
                        ecosystem_code=type_code,
                        ecosystem_label=type_code,
                        biome_name=str(row.get("zone") or "").strip(),
                        realm_name="Terrestrial",
                        get_code=str(row.get("get") or "").strip(),
                    ),
                    **_rle_category_payload(str(row.get("RLE") or "").strip()),
                    **_epl_category_payload(str(row.get("EPL") or "").strip()),
                    "rle_matrix_bucket": str(row.get("RLE_EPL") or "").strip(),
                },
            }
        )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from terrestrial RLE x EPL integration output for matrix drilldowns.",
        coverage_geography="National by biome and ecosystem type",
    )


def _parse_epl_terr(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    required = {"epl_2018_types", "epl_2024_types"}
    _require_aliases(entry, csv_rows, required)
    points = []
    for year, alias in ((2018, "epl_2018_types"), (2024, "epl_2024_types")):
        for row in csv_rows[alias]:
            type_code = str(row.get("T_MAPCODE") or "").strip()
            biome_name = str(row.get("T_BIOME") or "").strip()
            epl_category = str(row.get("epl_nat_inv24") or row.get("epl_nat24") or row.get("epl_base24") or "").strip()
            value = _decimal(row.get("ext_vegrem")) or _decimal(row.get("ext_veg")) or Decimal("0")
            target_progress = _target_progress_from_epl(epl_category)
            points.append(
                {
                    "year": year,
                    "value_numeric": value,
                    "disaggregation": {
                        **_ecosystem_disaggregation(
                            ecosystem_code=type_code,
                            ecosystem_label=type_code,
                            biome_name=biome_name,
                            realm_name="Terrestrial",
                        ),
                        **_epl_category_payload(epl_category),
                        "target_progress": target_progress,
                        "target_progress_label": _target_progress_label(target_progress),
                    },
                }
            )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from terrestrial EPL type-level outputs with 2018 and 2024 protection classifications.",
        coverage_geography="National by biome and ecosystem type",
    )


def _parse_rle_est(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    required = {"est_integration", "est_metrics"}
    _require_aliases(entry, csv_rows, required)
    metrics_lookup = {
        _normalize_est_type(str(row.get("full_ecosystem_type_name") or "")): row for row in csv_rows["est_metrics"]
    }
    points = []
    for row in csv_rows["est_integration"]:
        type_label = str(row.get("type") or "").strip()
        metrics = metrics_lookup.get(_normalize_est_type(type_label), {})
        zone = str(row.get("zone") or "").strip()
        for year, rle_key in ((2018, "RLE18"), (2024, "RLE24")):
            points.append(
                {
                    "year": year,
                    "value_numeric": _decimal(row.get("extent")) or Decimal("0"),
                    "disaggregation": {
                        **_ecosystem_disaggregation(
                            ecosystem_code=_normalize_est_type(type_label),
                            ecosystem_label=type_label,
                            biome_name="",
                            realm_name="Estuarine",
                        ),
                        "ecoregion_code": slugify(zone).replace("-", "_").upper() or "UNKNOWN",
                        "ecoregion_name": zone or "Unknown",
                        **_rle_category_payload(str(metrics.get(rle_key) or row.get("RLE") or "").strip()),
                        **_epl_category_payload(str(row.get("EPL") or "").strip()),
                        "rle_matrix_bucket": str(row.get("RLE_EPL") or "").strip(),
                    },
                }
            )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from estuarine RLE integration and metrics outputs.",
        coverage_geography="National by estuarine zone and ecosystem type",
    )


def _parse_rle_est_matrix(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    _require_aliases(entry, csv_rows, {"est_integration"})
    points = []
    for row in csv_rows["est_integration"]:
        type_label = str(row.get("type") or "").strip()
        zone = str(row.get("zone") or "").strip()
        points.append(
            {
                "year": 2024,
                "value_numeric": _decimal(row.get("extent")) or Decimal("0"),
                "disaggregation": {
                    **_ecosystem_disaggregation(
                        ecosystem_code=_normalize_est_type(type_label),
                        ecosystem_label=type_label,
                        biome_name="",
                        realm_name="Estuarine",
                    ),
                    "ecoregion_code": slugify(zone).replace("-", "_").upper() or "UNKNOWN",
                    "ecoregion_name": zone or "Unknown",
                    **_rle_category_payload(str(row.get("RLE") or "").strip()),
                    **_epl_category_payload(str(row.get("EPL") or "").strip()),
                    "rle_matrix_bucket": str(row.get("RLE_EPL") or "").strip(),
                },
            }
        )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from estuarine RLE x EPL integration output for matrix drilldowns.",
        coverage_geography="National by estuarine zone and ecosystem type",
    )


def _parse_tepi_terr(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    _require_aliases(entry, csv_rows, {"tepi_biome"})
    points = []
    for row in csv_rows["tepi_biome"]:
        biome_name = str(row.get("BIOME") or "").strip()
        for year_key, raw_value in row.items():
            if not str(year_key).isdigit():
                continue
            value = _decimal(raw_value)
            if value is None:
                continue
            target_progress = _target_progress_from_ratio(value)
            points.append(
                {
                    "year": int(year_key),
                    "value_numeric": value,
                    "disaggregation": {
                        "biome_code": _biome_code(biome_name),
                        "biome_name": biome_name,
                        "target_progress": target_progress,
                        "target_progress_label": _target_progress_label(target_progress),
                    },
                }
            )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from TEPI biome timeseries output.",
        coverage_geography="National by biome",
    )


def _parse_plant_spi_demo(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]]) -> ParsedIndicatorPayload:
    _require_aliases(entry, csv_rows, {"spi_demo"})
    points = []
    for row in csv_rows["spi_demo"]:
        spi_category = str(row.get("spi_category") or "").strip()
        points.append(
            {
                "year": int(str(row.get("year") or "0")),
                "value_numeric": _decimal(row.get("spi_value")) or Decimal("0"),
                "disaggregation": {
                    "province_code": str(row.get("province_code") or "").strip(),
                    "province_name": str(row.get("province_name") or "").strip(),
                    "biome_code": str(row.get("biome_code") or "").strip(),
                    "biome_name": str(row.get("biome_name") or "").strip(),
                    "taxonomy_kingdom": str(row.get("taxonomy_kingdom") or "").strip(),
                    "taxonomy_phylum": str(row.get("taxonomy_phylum") or "").strip(),
                    "taxonomy_class": str(row.get("taxonomy_class") or "").strip(),
                    "taxonomy_order": str(row.get("taxonomy_order") or "").strip(),
                    "taxonomy_family": str(row.get("taxonomy_family") or "").strip(),
                    "taxonomy_genus": str(row.get("taxonomy_genus") or "").strip(),
                    "taxonomy_species": str(row.get("taxonomy_species") or "").strip(),
                    "spi_category": spi_category,
                    "spi_category_label": EPL_LABELS.get(spi_category, spi_category),
                    "protection_category": spi_category,
                    "protection_category_label": EPL_LABELS.get(spi_category, spi_category),
                },
            }
        )
    return _build_payload(
        entry=entry,
        points=points,
        source_notes="Parsed from curated plant SPI demo output derived from the published protection-level methodology.",
        coverage_geography="National by province and taxonomy",
    )


def _build_payload(
    *,
    entry: dict[str, Any],
    points: list[dict[str, Any]],
    source_notes: str,
    coverage_geography: str,
) -> ParsedIndicatorPayload:
    if not points:
        raise PilotIngestError(f"{entry['indicator_code']} did not produce any indicator data points.")
    years = sorted({int(point["year"]) for point in points})
    return ParsedIndicatorPayload(
        title=str(entry["indicator_title"]),
        unit=str(entry.get("unit") or ""),
        value_type=_indicator_value_type(str(entry.get("value_type") or "numeric")),
        methodology=str(entry.get("method_metadata", {}).get("name") or entry["indicator_title"]),
        source_notes=source_notes,
        disaggregation_schema=_build_disaggregation_schema(points),
        points=points,
        coverage_geography=coverage_geography,
        coverage_time_start_year=years[0] if years else None,
        coverage_time_end_year=years[-1] if years else None,
    )


def _upsert_dataset(*, entry: dict[str, Any], organisation: Organisation, license_obj: License | None) -> Dataset:
    dataset, _created = Dataset.objects.update_or_create(
        dataset_code=f"DS-{entry['indicator_code']}",
        defaults={
            "title": entry["indicator_title"],
            "description": entry["dataset_metadata"].get("description") or entry["indicator_title"],
            "methodology": entry["method_metadata"].get("name") or entry["indicator_title"],
            "source_url": entry["repo_url"],
            "license": license_obj,
            "metadata_json": {
                "provider": entry["dataset_metadata"].get("provider"),
                "owner_org": entry["dataset_metadata"].get("owner_org"),
                "licence_title": entry["dataset_metadata"].get("licence_title"),
                "licence_code": entry["dataset_metadata"].get("licence_code"),
                "embargo_note": entry["dataset_metadata"].get("embargo_note") or "",
            },
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": _sensitivity(entry["dataset_metadata"].get("sensitivity")),
            "export_approved": _sensitivity(entry["dataset_metadata"].get("sensitivity")) == SensitivityLevel.PUBLIC,
            "review_note": "Licence unknown; verify." if str(entry["dataset_metadata"].get("licence_code")) == "LIC-UNKNOWN" else "",
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )
    return dataset


def _upsert_dataset_release(
    *,
    entry: dict[str, Any],
    dataset: Dataset,
    organisation: Organisation,
    release_date: date | None,
    asset_manifest: list[dict[str, Any]],
    manifest_version: str,
) -> DatasetRelease:
    version = f"{Path(str(entry['repo_url']).rstrip('/')).name}@{str(entry['repo_ref'])[:12]}"
    release, _created = DatasetRelease.objects.update_or_create(
        dataset=dataset,
        version=version,
        defaults={
            "release_date": release_date,
            "snapshot_title": f"{entry['indicator_title']} ({version})",
            "snapshot_description": entry["dataset_metadata"].get("description") or entry["indicator_title"],
            "snapshot_methodology": entry["method_metadata"].get("name") or entry["indicator_title"],
            "provenance_json": {
                "manifest_version": manifest_version,
                "repo_url": entry["repo_url"],
                "repo_ref": entry["repo_ref"],
                "repo_ref_date": entry.get("repo_ref_date"),
                "retrieved_at_utc": timezone.now().isoformat(),
                "file_paths": [file_spec["path"] for file_spec in entry.get("files", [])],
            },
            "asset_manifest_json": asset_manifest,
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": dataset.sensitivity,
            "export_approved": dataset.export_approved,
            "review_note": dataset.review_note,
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )
    return release


def _upsert_indicator(
    *,
    entry: dict[str, Any],
    organisation: Organisation,
    release_date: date | None,
    parsed: ParsedIndicatorPayload,
) -> Indicator:
    national_target = _ensure_national_target(entry=entry, organisation=organisation)
    indicator, _created = Indicator.objects.update_or_create(
        code=entry["indicator_code"],
        defaults={
            "title": entry["indicator_title"],
            "national_target": national_target,
            "indicator_type": _indicator_type(str(entry.get("indicator_type") or "headline")),
            "reporting_cadence": UpdateFrequency.ANNUAL,
            "qa_status": QaStatus.PUBLISHED,
            "responsible_org": organisation,
            "owner_organisation": organisation,
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": _sensitivity(entry["dataset_metadata"].get("sensitivity")),
            "export_approved": _sensitivity(entry["dataset_metadata"].get("sensitivity")) == SensitivityLevel.PUBLIC,
            "reporting_capability": IndicatorReportingCapability.YES,
            "update_frequency": UpdateFrequency.ANNUAL,
            "last_updated_on": release_date,
            "coverage_geography": parsed.coverage_geography,
            "coverage_time_start_year": parsed.coverage_time_start_year,
            "coverage_time_end_year": parsed.coverage_time_end_year,
            "computation_notes": parsed.source_notes,
            "limitations": "NBMS ingests pinned workflow outputs; source workflows remain external and authoritative.",
            "data_quality_note": "Pilot ingest from pinned GitHub output tables with governed provenance.",
            "review_note": "Licence unknown; verify." if _sensitivity(entry["dataset_metadata"].get("sensitivity")) != SensitivityLevel.PUBLIC else "",
            "visual_pack_id": str(entry.get("pack_id") or ""),
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )
    return indicator


def _link_dataset(*, entry: dict[str, Any], indicator: Indicator, dataset: Dataset) -> None:
    IndicatorDatasetLink.objects.update_or_create(
        indicator=indicator,
        dataset=dataset,
        defaults={"note": f"Pilot dataset ingest from {entry['repo_url']}@{str(entry['repo_ref'])[:12]}."},
    )


def _upsert_methodology(
    *,
    entry: dict[str, Any],
    indicator: Indicator,
    organisation: Organisation,
    release_date: date | None,
) -> None:
    method_metadata = entry["method_metadata"]
    methodology, _created = Methodology.objects.update_or_create(
        methodology_code=method_metadata["methodology_code"],
        defaults={
            "title": method_metadata["name"],
            "description": "Methodology metadata for externally produced NBA workflow outputs ingested into NBMS.",
            "owner_org": organisation,
            "scope": entry.get("realm") or "national",
            "references_url": method_metadata.get("protocol_url") or entry["repo_url"],
            "is_active": True,
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )
    method_version, _created = MethodologyVersion.objects.update_or_create(
        methodology=methodology,
        version=str(method_metadata["version_label"]),
        defaults={
            "status": MethodologyStatus.ACTIVE,
            "effective_date": release_date,
            "change_log": f"Derived from pinned GitHub workflow output {entry['repo_url']}@{entry['repo_ref']}.",
            "protocol_url": method_metadata.get("protocol_url") or entry["repo_url"],
            "qa_steps_summary": "NBMS bronze asset capture, column validation, and deterministic point rebuild.",
            "approval_body": method_metadata.get("approval_body") or "NBMS pilot ingest",
            "is_active": True,
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )
    IndicatorMethodologyVersionLink.objects.update_or_create(
        indicator=indicator,
        methodology_version=method_version,
        defaults={
            "is_primary": True,
            "notes": "Pinned methodology version for pilot workflow output ingest.",
            "source": entry["repo_url"],
            "is_active": True,
        },
    )
    MethodologyIndicatorLink.objects.update_or_create(
        methodology=methodology,
        indicator=indicator,
        defaults={
            "relationship_type": RelationshipType.DERIVED,
            "role": "primary",
            "notes": "Indicator derived from externally produced workflow outputs.",
            "is_active": True,
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )


def _upsert_method_profile(*, indicator: Indicator, entry: dict[str, Any], parsed: ParsedIndicatorPayload) -> None:
    IndicatorMethodProfile.objects.update_or_create(
        indicator=indicator,
        method_type=IndicatorMethodType.CSV_IMPORT,
        implementation_key="nba_pilot_output_ingest",
        defaults={
            "summary": "NBMS ingests pinned NBA workflow outputs without re-implementing the source R workflow.",
            "required_inputs_json": [file_spec["path"] for file_spec in entry.get("files", [])],
            "disaggregation_requirements_json": sorted(parsed.disaggregation_schema.keys()),
            "output_schema_json": parsed.disaggregation_schema,
            "readiness_state": IndicatorMethodReadiness.READY,
            "readiness_notes": "Ready when the pinned bronze assets and manifest remain available.",
            "is_active": True,
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )


def _upsert_evidence(*, entry: dict[str, Any], indicator: Indicator, organisation: Organisation) -> list[str]:
    codes: list[str] = []
    for index, evidence in enumerate(entry.get("evidence_urls", []), start=1):
        code = f"EV-{entry['indicator_code']}-{index}"
        evidence_obj, _created = Evidence.objects.update_or_create(
            evidence_code=code,
            defaults={
                "title": evidence["title"],
                "description": f"Pilot evidence link for {entry['indicator_title']}.",
                "evidence_type": "url",
                "source_url": evidence["url"],
                "organisation": organisation,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": _sensitivity(entry["dataset_metadata"].get("sensitivity")),
                "export_approved": _sensitivity(entry["dataset_metadata"].get("sensitivity")) == SensitivityLevel.PUBLIC,
            },
        )
        IndicatorEvidenceLink.objects.update_or_create(
            indicator=indicator,
            evidence=evidence_obj,
            defaults={"note": "Pilot ingest evidence and provenance link."},
        )
        codes.append(code)
    return codes


def _upsert_series_and_points(
    *,
    indicator: Indicator,
    dataset_release: DatasetRelease,
    organisation: Organisation,
    parsed: ParsedIndicatorPayload,
    entry: dict[str, Any],
) -> None:
    series, _created = IndicatorDataSeries.objects.update_or_create(
        indicator=indicator,
        defaults={
            "series_code": f"SER-{indicator.code}",
            "title": parsed.title,
            "unit": parsed.unit,
            "value_type": parsed.value_type,
            "methodology": parsed.methodology,
            "disaggregation_schema": parsed.disaggregation_schema,
            "source_notes": parsed.source_notes,
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": indicator.sensitivity,
            "export_approved": indicator.sensitivity == SensitivityLevel.PUBLIC,
        },
    )
    IndicatorDataPoint.objects.filter(series=series, dataset_release=dataset_release).delete()
    source_url = f"{entry['repo_url']}/tree/{entry['repo_ref']}"
    point_rows = [
        IndicatorDataPoint(
            series=series,
            year=int(point["year"]),
            value_numeric=point.get("value_numeric"),
            value_text=point.get("value_text") or "",
            disaggregation=point.get("disaggregation") or {},
            dataset_release=dataset_release,
            source_url=source_url,
            footnote="Pilot ingest from pinned workflow output.",
        )
        for point in parsed.points
    ]
    IndicatorDataPoint.objects.bulk_create(point_rows)


def _upsert_mea_mappings(*, entry: dict[str, Any], indicator: Indicator, organisation: Organisation) -> list[dict[str, Any]]:
    national_target = indicator.national_target
    mappings: list[dict[str, Any]] = []
    for gbf_target_code in entry.get("mea_mappings", {}).get("gbf_targets", []):
        framework_target = _ensure_framework_target(
            framework_code="GBF",
            target_code=str(gbf_target_code),
            target_title=GBF_TARGETS[str(gbf_target_code)][1],
            organisation=organisation,
        )
        NationalTargetFrameworkTargetLink.objects.update_or_create(
            national_target=national_target,
            framework_target=framework_target,
            defaults={
                "relation_type": AlignmentRelationType.CONTRIBUTES_TO,
                "confidence": 85,
                "notes": "Pilot mapping from NBA indicator ingest manifest.",
                "source": entry["repo_url"],
                "is_active": True,
            },
        )
        framework_indicator = _ensure_framework_indicator(
            framework_target=framework_target,
            indicator_code=f"GBF-PILOT-{gbf_target_code}-{indicator.code}",
            indicator_title=indicator.title,
            organisation=organisation,
        )
        IndicatorFrameworkIndicatorLink.objects.update_or_create(
            indicator=indicator,
            framework_indicator=framework_indicator,
            defaults={
                "relation_type": AlignmentRelationType.CONTRIBUTES_TO,
                "confidence": 85,
                "notes": "Pilot mapping from NBA indicator ingest manifest.",
                "source": entry["repo_url"],
                "is_active": True,
            },
        )
        mappings.append({"framework_code": "GBF", "target_code": framework_target.code, "indicator_code": framework_indicator.code})

    for secondary in entry.get("mea_mappings", {}).get("secondary_frameworks", []):
        framework_target = _ensure_framework_target(
            framework_code=str(secondary["framework_code"]),
            target_code=str(secondary["target_code"]),
            target_title=str(secondary.get("target_title") or ""),
            organisation=organisation,
        )
        NationalTargetFrameworkTargetLink.objects.update_or_create(
            national_target=national_target,
            framework_target=framework_target,
            defaults={
                "relation_type": AlignmentRelationType.SUPPORTS,
                "confidence": 40,
                "notes": "Secondary pilot mapping pending expert review.",
                "source": entry["repo_url"],
                "is_active": True,
            },
        )
        framework_indicator = _ensure_framework_indicator(
            framework_target=framework_target,
            indicator_code=str(secondary["indicator_code"]),
            indicator_title=str(secondary["indicator_title"]),
            organisation=organisation,
        )
        IndicatorFrameworkIndicatorLink.objects.update_or_create(
            indicator=indicator,
            framework_indicator=framework_indicator,
            defaults={
                "relation_type": AlignmentRelationType.SUPPORTS,
                "confidence": 40,
                "notes": "Secondary pilot mapping pending expert review.",
                "source": entry["repo_url"],
                "is_active": True,
            },
        )
        mappings.append(
            {
                "framework_code": framework_target.framework.code,
                "target_code": framework_target.code,
                "indicator_code": framework_indicator.code,
            }
        )
    return mappings


def _ensure_organisation(*, code: str, name: str) -> Organisation:
    organisation, _created = Organisation.objects.update_or_create(
        org_code=code,
        defaults={
            "name": name,
            "is_active": True,
            "source_system": "nba_pilot_ingest",
            "source_ref": code,
        },
    )
    return organisation


def _ensure_license(dataset_metadata: dict[str, Any]) -> License | None:
    code = str(dataset_metadata.get("licence_code") or "").strip()
    if not code:
        return None
    license_obj, _created = License.objects.update_or_create(
        code=code,
        defaults={
            "title": str(dataset_metadata.get("licence_title") or code),
            "url": str(dataset_metadata.get("licence_url") or ""),
            "description": str(dataset_metadata.get("licence_title") or ""),
            "is_active": True,
        },
    )
    return license_obj


def _ensure_national_target(*, entry: dict[str, Any], organisation: Organisation) -> NationalTarget:
    target_metadata = entry["national_target"]
    national_target, _created = NationalTarget.objects.update_or_create(
        code=target_metadata["code"],
        defaults={
            "title": target_metadata["title"],
            "description": f"Pilot national target scaffold for {entry['indicator_title']}.",
            "responsible_org": organisation,
            "qa_status": QaStatus.PUBLISHED,
            "reporting_cadence": UpdateFrequency.ANNUAL,
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": _sensitivity(entry["dataset_metadata"].get("sensitivity")),
            "source_system": "nba_pilot_ingest",
            "source_ref": str(entry["repo_ref"]),
        },
    )
    return national_target


def _ensure_framework_target(
    *,
    framework_code: str,
    target_code: str,
    target_title: str,
    organisation: Organisation,
) -> FrameworkTarget:
    framework = _ensure_framework(framework_code=framework_code, organisation=organisation)
    goal = None
    normalized_framework = framework.code.upper()
    if normalized_framework == "GBF":
        goal_code, goal_title = GBF_TARGETS[str(target_code)][0], GBF_GOALS[GBF_TARGETS[str(target_code)][0]]
        goal = _ensure_framework_goal(framework=framework, goal_code=goal_code, goal_title=goal_title, organisation=organisation)
    elif normalized_framework == "SDG":
        goal = _ensure_framework_goal(framework=framework, goal_code=str(target_code), goal_title=target_title, organisation=organisation)
    target, _created = FrameworkTarget.objects.update_or_create(
        framework=framework,
        code=target_code,
        defaults={
            "goal": goal,
            "title": target_title or f"{framework.code} {target_code}",
            "description": target_title or f"{framework.code} {target_code}",
            "official_text": target_title or f"{framework.code} {target_code}",
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "review_note": "Pending expert review." if normalized_framework != "GBF" else "",
            "source_system": "nba_pilot_ingest",
            "source_ref": framework.code,
        },
    )
    return target


def _ensure_framework_indicator(
    *,
    framework_target: FrameworkTarget,
    indicator_code: str,
    indicator_title: str,
    organisation: Organisation,
) -> FrameworkIndicator:
    framework_indicator, _created = FrameworkIndicator.objects.update_or_create(
        framework=framework_target.framework,
        code=indicator_code,
        defaults={
            "framework_target": framework_target,
            "title": indicator_title,
            "description": f"Pilot framework indicator scaffold for {indicator_title}.",
            "indicator_type": FrameworkIndicatorType.HEADLINE,
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "review_note": "Pending expert review." if framework_target.framework.code != "GBF" else "",
            "source_system": "nba_pilot_ingest",
            "source_ref": indicator_code,
        },
    )
    return framework_indicator


def _ensure_framework(*, framework_code: str, organisation: Organisation) -> Framework:
    normalized = framework_code.upper()
    title = (
        "Kunming-Montreal Global Biodiversity Framework"
        if normalized == "GBF"
        else SECONDARY_FRAMEWORKS.get(normalized, {}).get("title", normalized)
    )
    framework, _created = Framework.objects.update_or_create(
        code=normalized,
        defaults={
            "title": title,
            "description": f"{title} scaffold for pilot indicator mappings.",
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "review_note": "Pending expert review." if normalized != "GBF" else "",
        },
    )
    return framework


def _ensure_framework_goal(*, framework: Framework, goal_code: str, goal_title: str, organisation: Organisation) -> FrameworkGoal:
    goal, _created = FrameworkGoal.objects.update_or_create(
        framework=framework,
        code=goal_code,
        defaults={
            "title": goal_code if framework.code != "GBF" else f"Goal {goal_code}",
            "official_text": goal_title,
            "description": goal_title,
            "sort_order": _goal_sort_order(goal_code),
            "organisation": organisation,
            "status": LifecycleStatus.PUBLISHED,
            "sensitivity": SensitivityLevel.PUBLIC,
            "is_active": True,
            "source_system": "nba_pilot_ingest",
            "source_ref": goal_code,
        },
    )
    return goal


def _goal_sort_order(goal_code: str) -> int:
    if goal_code.isdigit():
        return int(goal_code)
    return {"A": 1, "B": 2, "C": 3, "D": 4}.get(goal_code, 99)


def _ecosystem_disaggregation(
    *,
    ecosystem_code: str,
    ecosystem_label: str,
    biome_name: str,
    realm_name: str,
    get_code: str = "",
) -> dict[str, str]:
    payload = {
        "ecosystem_type": ecosystem_code,
        "ecosystem_type_label": ecosystem_label or ecosystem_code,
        "realm_code": slugify(realm_name).replace("-", "_").upper() or "UNKNOWN",
        "realm_name": realm_name or "Unknown",
    }
    if biome_name:
        payload["biome_code"] = _biome_code(biome_name)
        payload["biome_name"] = biome_name
    if get_code:
        payload["get_code"] = get_code
    return payload


def _rle_category_payload(code: str) -> dict[str, str]:
    return {
        "rle_category": code,
        "rle_category_label": RLE_LABELS.get(code, code),
        "threat_category": code,
        "threat_category_label": RLE_LABELS.get(code, code),
    }


def _epl_category_payload(code: str) -> dict[str, str]:
    return {
        "epl_category": code,
        "epl_category_label": EPL_LABELS.get(code, code),
        "protection_category": code,
        "protection_category_label": EPL_LABELS.get(code, code),
    }


def _target_progress_from_epl(code: str) -> str:
    if code == "WP":
        return "ON_TRACK"
    if code in {"MP", "PP"}:
        return "ACCELERATE"
    return "OFF_TRACK"


def _target_progress_from_ratio(value: Decimal) -> str:
    if value >= Decimal("0.30"):
        return "ON_TRACK"
    if value >= Decimal("0.20"):
        return "ACCELERATE"
    return "OFF_TRACK"


def _target_progress_label(code: str) -> str:
    return {
        "ON_TRACK": "On track",
        "ACCELERATE": "Needs acceleration",
        "OFF_TRACK": "Off track",
    }.get(code, code)


def _build_disaggregation_schema(points: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    keys: set[str] = set()
    for point in points:
        keys.update((point.get("disaggregation") or {}).keys())
    return {key: {"type": "string"} for key in sorted(keys)}


def _indicator_type(value: str) -> str:
    value = value.strip().lower()
    mapping = {
        "headline": NationalIndicatorType.HEADLINE,
        "binary": NationalIndicatorType.BINARY,
        "component": NationalIndicatorType.COMPONENT,
        "complementary": NationalIndicatorType.COMPLEMENTARY,
        "national": NationalIndicatorType.NATIONAL,
    }
    return mapping.get(value, NationalIndicatorType.OTHER)


def _indicator_value_type(value: str) -> str:
    value = value.strip().lower()
    mapping = {
        "numeric": IndicatorValueType.NUMERIC,
        "percent": IndicatorValueType.PERCENT,
        "index": IndicatorValueType.INDEX,
        "text": IndicatorValueType.TEXT,
    }
    return mapping.get(value, IndicatorValueType.NUMERIC)


def _sensitivity(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "public":
        return SensitivityLevel.PUBLIC
    if normalized == "restricted":
        return SensitivityLevel.RESTRICTED
    if normalized == "iplc_sensitive":
        return SensitivityLevel.IPLC_SENSITIVE
    return SensitivityLevel.INTERNAL


def _decimal(value: Any) -> Decimal | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def _parse_iso_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return date.fromisoformat(raw[:10])


def _biome_code(name: str) -> str:
    normalized = str(name or "").strip()
    if normalized in BIOME_CODE_MAP:
        return BIOME_CODE_MAP[normalized]
    return slugify(normalized).replace("-", "_").upper() or "UNKNOWN"


def _normalize_est_type(value: str) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if normalized and normalized[0].isdigit():
        _, _, normalized = normalized.partition(" ")
    return normalized.strip()


def _require_aliases(entry: dict[str, Any], csv_rows: dict[str, list[dict[str, str]]], required: set[str]) -> None:
    missing = sorted(alias for alias in required if alias not in csv_rows)
    if missing:
        raise PilotIngestError(f"{entry['indicator_code']} is missing required CSV aliases: {', '.join(missing)}")
