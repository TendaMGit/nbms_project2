from __future__ import annotations

import hashlib
import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from nbms_app.models import (
    EcosystemType,
    EcosystemTypologyCrosswalk,
    IucnGetNode,
    LifecycleStatus,
    Organisation,
    QaStatus,
    RegistryReviewStatus,
    SensitivityLevel,
    SpatialIngestionStatus,
    SpatialLayer,
    SpatialLayerSourceType,
    SpatialSource,
    SpatialSourceFormat,
    SpatialSourceSyncStatus,
    SpatialFeature,
    UpdateFrequency,
)
from nbms_app.services.spatial_ingest import ingest_spatial_file


PROPERTY_CODE_KEYS = [
    "veg_code",
    "VEG_CODE",
    "MUCINA_L2",
    "MUCINA_L3",
    "eco_code",
    "ECO_CODE",
    "code",
    "CODE",
]
PROPERTY_NAME_KEYS = [
    "veg_name",
    "VEG_NAME",
    "MUCINA_VEG",
    "NAME",
    "name",
]
PROPERTY_BIOME_KEYS = ["biome", "BIOME", "BIOME_NAME", "bio_name", "BIO_NAME"]
PROPERTY_BIOREGION_KEYS = ["bioregion", "BIOREGION", "eco_region", "ECO_REGION"]
PROPERTY_REALM_KEYS = ["realm", "REALM", "realm_name", "REALM_NAME"]


def _pick(props: dict, keys: list[str]) -> str:
    for key in keys:
        value = props.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _detect_realm(props: dict) -> str:
    explicit = _pick(props, PROPERTY_REALM_KEYS).lower()
    if explicit:
        if "marine" in explicit:
            return "marine"
        if "fresh" in explicit:
            return "freshwater"
        return "terrestrial"

    words = " ".join(
        [
            _pick(props, PROPERTY_BIOME_KEYS),
            _pick(props, PROPERTY_NAME_KEYS),
        ]
    ).lower()
    if any(token in words for token in ["marine", "ocean", "coastal", "estuary"]):
        return "marine"
    if any(token in words for token in ["river", "wetland", "freshwater", "lake"]):
        return "freshwater"
    return "terrestrial"


def _download_to_temp(url: str) -> tuple[Path, str, str]:
    parsed = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name or "vegmap_source.bin"
    with urllib.request.urlopen(url, timeout=180) as response:
        digest = hashlib.sha256()
        suffix = Path(filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                if not chunk:
                    break
                digest.update(chunk)
                handle.write(chunk)
            temp_path = Path(handle.name)
    return temp_path, filename, digest.hexdigest()


def _realm_get_code(realm: str) -> str:
    value = (realm or "").lower()
    if value == "marine":
        return "L1-Marine"
    if value == "freshwater":
        return "L1-Freshwater"
    return "L1-Terrestrial"


class Command(BaseCommand):
    help = "Sync VegMap baseline from URL/file and update ecosystem registry with GET crosswalk placeholders."

    def add_arguments(self, parser):
        parser.add_argument("--source-url", default="", help="Optional online source URL.")
        parser.add_argument("--file", default="", help="Local GeoJSON/GPKG/Shapefile path.")
        parser.add_argument("--source-code", default="VEGMAP_BASELINE")
        parser.add_argument("--layer-code", default="ZA_VEGMAP_BASELINE")
        parser.add_argument("--vegmap-version", default="unknown")
        parser.add_argument("--country-iso3", default="ZAF")
        parser.add_argument(
            "--use-demo-layer",
            action="store_true",
            help="Use existing ZA_ECOSYSTEM_PROXY_NE layer if no source file/url is provided.",
        )
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        source_url = (options.get("source_url") or "").strip()
        source_file = (options.get("file") or "").strip()
        source_code = (options.get("source_code") or "VEGMAP_BASELINE").strip().upper()
        layer_code = (options.get("layer_code") or "ZA_VEGMAP_BASELINE").strip().upper()
        vegmap_version = (options.get("vegmap_version") or "unknown").strip()
        country_iso3 = (options.get("country_iso3") or "ZAF").strip().upper()
        use_demo_layer = bool(options.get("use_demo_layer"))
        dry_run = bool(options.get("dry_run"))

        call_command("seed_get_reference", verbosity=0)
        sanbi, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute", "org_type": "Government"},
        )

        temp_path = None
        source_filename = ""
        source_checksum = ""
        source = None
        layer = None

        if source_file or source_url:
            source_defaults = {
                "title": "VegMap Baseline",
                "description": "VegMap-centric ecosystem baseline source for NBMS ecosystem registry.",
                "source_url": source_url or "file://local-upload",
                "source_format": SpatialSourceFormat.OTHER,
                "license": "As provided by source authority",
                "attribution": "SANBI / source authority",
                "requires_token": False,
                "update_frequency": UpdateFrequency.ANNUAL,
                "enabled_by_default": True,
                "source_type": SpatialLayerSourceType.UPLOADED_FILE,
                "layer_code": layer_code,
                "layer_title": "VegMap Baseline",
                "layer_description": "VegMap baseline layer",
                "theme": "GBF",
                "sensitivity": SensitivityLevel.PUBLIC,
                "consent_required": False,
                "export_approved": True,
                "is_public": True,
                "publish_to_geoserver": True,
                "country_iso3": country_iso3,
                "organisation": sanbi,
            }
            source, _ = SpatialSource.objects.update_or_create(code=source_code, defaults=source_defaults)

            layer, _ = SpatialLayer.objects.update_or_create(
                layer_code=layer_code,
                defaults={
                    "title": "VegMap Baseline",
                    "name": "VegMap Baseline",
                    "slug": layer_code.lower().replace("_", "-"),
                    "description": "VegMap baseline source for ecosystem registry.",
                    "source_type": SpatialLayerSourceType.UPLOADED_FILE,
                    "data_ref": "nbms_app_spatialfeature",
                    "theme": "GBF",
                    "default_style_json": {"fillColor": "#4f772d", "lineColor": "#31572c"},
                    "attribution": source.attribution,
                    "license": source.license,
                    "update_frequency": UpdateFrequency.ANNUAL,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "consent_required": False,
                    "export_approved": True,
                    "is_public": True,
                    "is_active": True,
                    "publish_to_geoserver": True,
                    "organisation": sanbi,
                    "spatial_source": source,
                },
            )

            if source_file:
                file_path = Path(source_file)
                if not file_path.exists():
                    raise CommandError(f"File not found: {source_file}")
                source_filename = file_path.name
                source_checksum = hashlib.sha256(file_path.read_bytes()).hexdigest()
                ingest_path = file_path
            else:
                temp_path, source_filename, source_checksum = _download_to_temp(source_url)
                ingest_path = temp_path

            if source_filename.lower().endswith(".geojson") or source_filename.lower().endswith(".json"):
                source.source_format = SpatialSourceFormat.GEOJSON
            elif source_filename.lower().endswith(".gpkg"):
                source.source_format = SpatialSourceFormat.GPKG
            elif source_filename.lower().endswith(".zip"):
                source.source_format = SpatialSourceFormat.ZIP_SHAPEFILE
            elif source_filename.lower().endswith(".shp"):
                source.source_format = SpatialSourceFormat.SHAPEFILE
            source.last_checksum = source_checksum
            source.last_sync_at = timezone.now()

            if dry_run:
                source.last_status = SpatialSourceSyncStatus.READY
                source.last_error = ""
                source.save(update_fields=["source_format", "last_checksum", "last_sync_at", "last_status", "last_error", "updated_at"])
                self.stdout.write("Dry-run mode: skipped VegMap ingest.")
            else:
                run = ingest_spatial_file(
                    layer=layer,
                    file_path=str(ingest_path),
                    source_filename=source_filename,
                    source_layer_name=source.source_layer_name or None,
                    source_storage_path="",
                    source=source,
                    country_iso3=country_iso3 or None,
                )
                layer.latest_ingestion_run = run
                layer.save(update_fields=["latest_ingestion_run", "updated_at"])
                if run.status != SpatialIngestionStatus.SUCCEEDED:
                    source.last_status = SpatialSourceSyncStatus.FAILED
                    source.last_error = json.dumps(run.report_json or {}, sort_keys=True)
                    source.save(update_fields=["last_status", "last_error", "updated_at"])
                    raise CommandError(f"VegMap ingest failed. run_id={run.run_id}")
                source.last_status = SpatialSourceSyncStatus.READY
                source.last_error = ""
                source.last_feature_count = run.rows_ingested
                source.save(
                    update_fields=[
                        "source_format",
                        "last_checksum",
                        "last_sync_at",
                        "last_status",
                        "last_error",
                        "last_feature_count",
                        "updated_at",
                    ]
                )
        elif use_demo_layer:
            layer = SpatialLayer.objects.filter(layer_code="ZA_ECOSYSTEM_PROXY_NE", is_active=True).order_by("id").first()
            if not layer:
                raise CommandError("Demo layer ZA_ECOSYSTEM_PROXY_NE not found. Run sync_spatial_sources first.")
        else:
            raise CommandError("Provide --file or --source-url, or use --use-demo-layer.")

        if not layer:
            raise CommandError("No source layer available for ecosystem extraction.")

        features = SpatialFeature.objects.filter(layer=layer).order_by("feature_key", "id")
        if not features.exists():
            raise CommandError(f"Layer {layer.layer_code} has no features to extract ecosystem rows.")

        created_or_updated = 0
        crosswalk_count = 0
        get_nodes = {node.code: node for node in IucnGetNode.objects.filter(level=1, is_active=True)}

        for index, feature in enumerate(features, start=1):
            props = feature.properties or feature.properties_json or {}
            eco_code = _pick(props, PROPERTY_CODE_KEYS) or f"{layer.layer_code}-{index:05d}"
            name = _pick(props, PROPERTY_NAME_KEYS) or feature.name or eco_code
            biome = _pick(props, PROPERTY_BIOME_KEYS)
            bioregion = _pick(props, PROPERTY_BIOREGION_KEYS)
            realm = _detect_realm(props)

            ecosystem, _ = EcosystemType.objects.update_or_create(
                ecosystem_code=eco_code,
                defaults={
                    "name": name,
                    "realm": realm,
                    "biome": biome,
                    "bioregion": bioregion,
                    "vegmap_version": vegmap_version,
                    "vegmap_source_id": feature.feature_id or feature.feature_key,
                    "description": "Ingested from VegMap baseline source.",
                    "organisation": sanbi,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.VALIDATED,
                    "export_approved": True,
                    "source_system": "vegmap_sync",
                    "source_ref": f"{source_code}:{layer.layer_code}",
                    "is_active": True,
                },
            )
            created_or_updated += 1

            get_code = _realm_get_code(realm)
            get_node = get_nodes.get(get_code)
            if get_node:
                _, _ = EcosystemTypologyCrosswalk.objects.update_or_create(
                    ecosystem_type=ecosystem,
                    get_node=get_node,
                    defaults={
                        "confidence": 30,
                        "evidence": "Auto-assigned realm-only mapping; full GET mapping requires reviewer confirmation.",
                        "review_status": RegistryReviewStatus.NEEDS_REVIEW,
                        "is_primary": True,
                        "status": LifecycleStatus.DRAFT,
                        "sensitivity": SensitivityLevel.INTERNAL,
                        "qa_status": QaStatus.DRAFT,
                        "export_approved": False,
                        "source_system": "vegmap_sync",
                        "source_ref": f"{source_code}:{ecosystem.ecosystem_code}",
                    },
                )
                crosswalk_count += 1

        if temp_path:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

        self.stdout.write(
            self.style.SUCCESS(
                f"VegMap sync complete. layer={layer.layer_code} ecosystem_rows={created_or_updated} "
                f"crosswalk_placeholders={crosswalk_count}."
            )
        )
