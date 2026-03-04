from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from nbms_app.models import Dataset, DatasetRelease, Indicator, ReportingCycle, SpatialLayer


pytestmark = pytest.mark.django_db


MANIFEST_PATH = Path("src/nbms_app/pilots/nba_pilot_v1.yml")
User = get_user_model()


def _login_superuser(client):
    admin = User.objects.create_superuser(
        username="pilot-admin",
        email="pilot-admin@example.com",
        password="pass1234",
    )
    client.force_login(admin)
    return admin


def test_ingest_nba_pilot_outputs_is_idempotent_and_records_provenance(tmp_path):
    log_path = tmp_path / "pilot-report.json"

    call_command("ingest_nba_pilot_outputs", manifest=str(MANIFEST_PATH), log_file=str(log_path))
    call_command("ingest_nba_pilot_outputs", manifest=str(MANIFEST_PATH), log_file=str(log_path))

    assert Indicator.objects.filter(code__startswith="NBA_").count() == 7
    assert Dataset.objects.filter(dataset_code__startswith="DS-NBA_").count() == 7
    assert DatasetRelease.objects.filter(dataset__dataset_code__startswith="DS-NBA_").count() == 7
    assert log_path.exists()

    dataset = Dataset.objects.get(dataset_code="DS-NBA_ECO_RLE_TERR")
    release = DatasetRelease.objects.get(dataset=dataset)
    assert dataset.license.code == "CC-BY-NC-4.0"
    assert dataset.metadata_json["provider"] == "SANBI-NBA"
    assert release.provenance_json["repo_url"] == "https://github.com/askowno/RLE_terr"
    assert release.provenance_json["repo_ref"] == "ac4d80ba627ddf4211515406d87c5f673414c887"
    assert "outputs/results_A3.csv" in release.provenance_json["file_paths"]
    assert any(asset["storage_path"].endswith("results_A3.csv") for asset in release.asset_manifest_json)


def test_ingested_rle_indicator_endpoints_return_non_empty_payloads(client):
    _login_superuser(client)
    ReportingCycle.objects.create(
        code="NR7-2024",
        title="NR7 2024",
        start_date=date(2018, 1, 1),
        end_date=date(2024, 12, 31),
        due_date=date(2025, 3, 31),
        is_active=True,
    )
    call_command("ingest_nba_pilot_outputs", manifest=str(MANIFEST_PATH), log_file="media/ingest_reports/test-rle.json")

    indicator = Indicator.objects.get(code="NBA_ECO_RLE_TERR")

    series_response = client.get(
        reverse("api_indicator_series_summary", args=[indicator.uuid]),
        {"agg": "year", "release": "latest_approved", "method": "current", "report_cycle": "NR7-2024"},
    )
    assert series_response.status_code == 200
    series_payload = series_response.json()
    assert series_payload["results"]
    assert series_payload["meta"]["release_used"]["version"].startswith("RLE_terr@")
    assert series_payload["meta"]["release_used"]["param"] == "latest_approved"
    assert series_payload["meta"]["method_used"]["param"] == "current"
    assert series_payload["meta"]["report_cycle"]["code"] == "NR7-2024"

    cube_response = client.get(
        reverse("api_indicator_cube", args=[indicator.uuid]),
        {"group_by": "rle_category,biome", "report_cycle": "NR7-2024"},
    )
    assert cube_response.status_code == 200
    cube_payload = cube_response.json()
    assert cube_payload["rows"]
    assert any(row["rle_category"] in {"CR", "EN", "VU", "NT", "LC"} for row in cube_payload["rows"])
    assert cube_payload["meta"]["applied_filters"]["report_cycle"] == "NR7-2024"

    dimensions_response = client.get(reverse("api_indicator_dimensions", args=[indicator.uuid]))
    assert dimensions_response.status_code == 200
    dimension_ids = {row["id"] for row in dimensions_response.json()["dimensions"]}
    assert {"rle_category", "epl_category", "biome", "ecosystem_type"} <= dimension_ids

    profile_response = client.get(reverse("api_indicator_visual_profile", args=[indicator.uuid]))
    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert profile_payload["packId"] == "ecosystem_rle"
    assert {"distribution", "matrix"} <= set(profile_payload["availableViews"])


def test_ingested_matrix_indicator_advertises_matrix_profile_and_rows(client):
    _login_superuser(client)
    call_command("ingest_nba_pilot_outputs", manifest=str(MANIFEST_PATH), log_file="media/ingest_reports/test-matrix.json")

    indicator = Indicator.objects.get(code="NBA_ECO_RLE_EPL_TERR_MATRIX")

    profile_response = client.get(reverse("api_indicator_visual_profile", args=[indicator.uuid]))
    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert profile_payload["packId"] == "ecosystem_rle_x_epl_matrix"
    assert profile_payload["defaultView"] == "matrix"
    assert {"matrix", "distribution"} <= set(profile_payload["availableViews"])

    cube_response = client.get(
        reverse("api_indicator_cube", args=[indicator.uuid]),
        {"group_by": "rle_category,epl_category"},
    )
    assert cube_response.status_code == 200
    cube_payload = cube_response.json()
    assert cube_payload["rows"]
    assert any(row["rle_category"] == "CR" for row in cube_payload["rows"])
    assert any(row["epl_category"] in {"WP", "MP", "PP", "NP"} for row in cube_payload["rows"])


def test_ingested_plant_spi_supports_taxonomy_dimensions_and_filters(client):
    _login_superuser(client)
    call_command("ingest_nba_pilot_outputs", manifest=str(MANIFEST_PATH), log_file="media/ingest_reports/test-plant.json")

    indicator = Indicator.objects.get(code="NBA_PLANT_SPI")

    dimensions_response = client.get(reverse("api_indicator_dimensions", args=[indicator.uuid]))
    assert dimensions_response.status_code == 200
    dimension_ids = {row["id"] for row in dimensions_response.json()["dimensions"]}
    assert {"spi_category", "taxonomy_family", "taxonomy_genus", "taxonomy_species"} <= dimension_ids

    profile_response = client.get(reverse("api_indicator_visual_profile", args=[indicator.uuid]))
    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert profile_payload["defaultView"] == "taxonomy"
    assert {"taxonomy", "distribution"} <= set(profile_payload["availableViews"])

    cube_response = client.get(
        reverse("api_indicator_cube", args=[indicator.uuid]),
        {
            "group_by": "taxonomy_family,spi_category",
            "tax_level": "family",
            "tax_code": "family:Proteaceae",
        },
    )
    assert cube_response.status_code == 200
    cube_payload = cube_response.json()
    assert cube_payload["rows"]
    assert all(row["taxonomy_family"] == "Proteaceae" for row in cube_payload["rows"])


def test_seed_indicator_workflow_v2_exposes_pilot_catalogue_and_biome_map(client):
    _login_superuser(client)
    call_command("seed_indicator_workflow_v2")

    assert Indicator.objects.filter(status="published").count() >= 25
    assert Indicator.objects.filter(code="NBA_TEPI_TERR", visual_pack_id="tepi_timeseries").exists()
    assert Indicator.objects.filter(code="DEMO_BINARY_GBF_REPORTING_COMPLETENESS", visual_pack_id="binary_admin_status").exists()
    assert SpatialLayer.objects.filter(layer_code="ZA_BIOMES").exists()

    indicator = Indicator.objects.get(code="NBA_TEPI_TERR")
    map_response = client.get(reverse("api_indicator_map", args=[indicator.uuid]), {"year": 2024})
    assert map_response.status_code == 200
    map_payload = map_response.json()
    assert map_payload["meta"]["join_dimension"] == "biome"
    assert any(feature["properties"].get("biome_code") == "FYN" for feature in map_payload["features"])
