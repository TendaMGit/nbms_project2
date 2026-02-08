import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from nbms_app.models import (
    SensitivityLevel,
    SpatialFeature,
    SpatialLayer,
    SpatialSource,
    SpatialSourceFormat,
    SpatialSourceSyncStatus,
    SpatialLayerSourceType,
)
from nbms_app.services.spatial_sources import sync_spatial_source, sync_spatial_sources
from nbms_app.services.spatial_sources import _prepare_ingest_file


pytestmark = pytest.mark.django_db


def test_sync_spatial_sources_command_dry_run_seeds_defaults():
    call_command("sync_spatial_sources", "--dry-run")
    assert SpatialSource.objects.filter(code="NE_ADMIN1_ZA").exists()
    assert SpatialSource.objects.filter(code="NE_PROTECTED_LANDS_ZA").exists()
    assert SpatialSource.objects.filter(code="NE_GEOREGIONS_ZA").exists()


def test_sync_spatial_sources_default_protected_source_uses_dffe_public_feed():
    call_command("sync_spatial_sources", "--dry-run")
    source = SpatialSource.objects.get(code="NE_PROTECTED_LANDS_ZA")
    assert "dpmegis.dpme.gov.za" in source.source_url
    assert source.source_format == SpatialSourceFormat.GEOJSON


def test_sync_spatial_source_blocks_when_token_missing(monkeypatch):
    monkeypatch.delenv("WDPA_API_TOKEN", raising=False)
    source = SpatialSource.objects.create(
        code="TOKEN_REQUIRED",
        title="Token source",
        source_url="https://example.org/file.geojson",
        source_format=SpatialSourceFormat.GEOJSON,
        requires_token=True,
        token_env_var="WDPA_API_TOKEN",
        source_type=SpatialLayerSourceType.UPLOADED_FILE,
        layer_code="TOKEN_LAYER",
        layer_title="Token Layer",
        layer_description="",
        sensitivity=SensitivityLevel.PUBLIC,
    )
    result = sync_spatial_source(source=source)
    source.refresh_from_db()
    assert result["status"] == SpatialSourceSyncStatus.BLOCKED
    assert source.last_status == SpatialSourceSyncStatus.BLOCKED
    assert "WDPA_API_TOKEN" in source.last_error


def test_sync_spatial_source_skips_when_checksum_unchanged(monkeypatch, tmp_path):
    payload = b'{"type":"FeatureCollection","features":[]}'
    source_file = Path(tmp_path) / "layer.geojson"
    source_file.write_bytes(payload)
    checksum = hashlib.sha256(payload).hexdigest()

    source = SpatialSource.objects.create(
        code="UNCHANGED_SOURCE",
        title="Unchanged source",
        source_url="https://example.org/layer.geojson",
        source_format=SpatialSourceFormat.GEOJSON,
        source_type=SpatialLayerSourceType.UPLOADED_FILE,
        layer_code="UNCHANGED_LAYER",
        layer_title="Unchanged layer",
        layer_description="",
        sensitivity=SensitivityLevel.PUBLIC,
        last_checksum=checksum,
    )

    monkeypatch.setattr(
        "nbms_app.services.spatial_sources._download_to_temp",
        lambda **kwargs: (source_file, "layer.geojson", checksum),
    )

    result = sync_spatial_source(source=source, force=False)
    source.refresh_from_db()
    assert result["status"] == SpatialSourceSyncStatus.SKIPPED
    assert source.last_status == SpatialSourceSyncStatus.SKIPPED


def test_sync_spatial_source_reuses_existing_snapshot_when_refresh_fails(monkeypatch):
    source = SpatialSource.objects.create(
        code="REFRESH_FAIL_SOURCE",
        title="Refresh fail source",
        source_url="https://example.org/layer.geojson",
        source_format=SpatialSourceFormat.GEOJSON,
        source_type=SpatialLayerSourceType.UPLOADED_FILE,
        layer_code="REFRESH_FAIL_LAYER",
        layer_title="Refresh fail layer",
        layer_description="",
        sensitivity=SensitivityLevel.PUBLIC,
        last_checksum="abc123",
    )
    layer = SpatialLayer.objects.create(
        layer_code=source.layer_code,
        name="Refresh fail layer",
        slug="refresh-fail-layer",
        source_type=SpatialLayerSourceType.UPLOADED_FILE,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    SpatialFeature.objects.create(
        layer=layer,
        feature_key="feature-1",
        properties={"name": "existing"},
        geometry_json={"type": "Point", "coordinates": [24.0, -28.0]},
    )

    monkeypatch.setattr(
        "nbms_app.services.spatial_sources._download_to_temp",
        lambda **kwargs: (_ for _ in ()).throw(OSError("temporary dns failure")),
    )

    result = sync_spatial_source(source=source, force=False)
    source.refresh_from_db()

    assert result["status"] == SpatialSourceSyncStatus.SKIPPED
    assert result["checksum"] == "abc123"
    assert source.last_status == SpatialSourceSyncStatus.SKIPPED
    assert "reused previous snapshot" in source.last_error


def test_sync_spatial_source_ingests_and_updates(monkeypatch, tmp_path):
    payload = b'{"type":"FeatureCollection","features":[]}'
    source_file = Path(tmp_path) / "layer.geojson"
    source_file.write_bytes(payload)
    checksum = hashlib.sha256(payload).hexdigest()

    source = SpatialSource.objects.create(
        code="INGEST_SOURCE",
        title="Ingest source",
        source_url="https://example.org/layer.geojson",
        source_format=SpatialSourceFormat.GEOJSON,
        source_type=SpatialLayerSourceType.UPLOADED_FILE,
        layer_code="INGEST_LAYER",
        layer_title="Ingest layer",
        layer_description="",
        sensitivity=SensitivityLevel.PUBLIC,
    )

    monkeypatch.setattr(
        "nbms_app.services.spatial_sources._download_to_temp",
        lambda **kwargs: (source_file, "layer.geojson", checksum),
    )
    monkeypatch.setattr(
        "nbms_app.services.spatial_sources.ingest_spatial_file",
        lambda **kwargs: SimpleNamespace(run_id="spatial-test", status="succeeded", rows_ingested=17, report_json={}),
    )

    result = sync_spatial_source(source=source, force=True)
    source.refresh_from_db()

    assert result["status"] == SpatialSourceSyncStatus.READY
    assert result["rows_ingested"] == 17
    assert source.last_status == SpatialSourceSyncStatus.READY
    assert source.last_feature_count == 17
    assert source.last_checksum == checksum


def test_sync_spatial_sources_include_optional_toggle():
    sync_spatial_sources(dry_run=True, seed_defaults=True, include_optional=False)
    enabled_count = SpatialSource.objects.filter(enabled_by_default=True, is_active=True).count()
    assert enabled_count >= 3


def test_prepare_ingest_file_converts_arcgis_json_geometry(tmp_path):
    payload = {
        "features": [
            {
                "attributes": {"OBJECTID": 1, "NAME": "Protected Area A"},
                "geometry": {"rings": [["30.0 -28.0", "31.0 -28.0", "31.0 -27.0", "30.0 -28.0"]]},
            }
        ]
    }
    source_path = Path(tmp_path) / "arcgis.json"
    source_path.write_text(json.dumps(payload), encoding="utf-8")

    converted_path = _prepare_ingest_file(source=SimpleNamespace(), file_path=source_path)
    assert converted_path != source_path
    assert converted_path.suffix.endswith("geojson")

    converted_payload = json.loads(converted_path.read_text(encoding="utf-8"))
    assert converted_payload["type"] == "FeatureCollection"
    assert len(converted_payload["features"]) == 1
    assert converted_payload["features"][0]["properties"]["NAME"] == "Protected Area A"
    assert converted_payload["features"][0]["geometry"]["type"] == "Polygon"
