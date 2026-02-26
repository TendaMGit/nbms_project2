from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import SpatialLayer, SpatialLayerSourceType
from nbms_app.services.spatial_ingest import ingest_spatial_file


class Command(BaseCommand):
    help = "Ingest a vector dataset (GeoJSON/GPKG/SHP/ZIP) into NBMS spatial feature store."

    def add_arguments(self, parser):
        parser.add_argument("--layer-code", required=True)
        parser.add_argument("--file", required=True)
        parser.add_argument("--title", default="")
        parser.add_argument("--source-layer-name", default="")

    def handle(self, *args, **options):
        layer_code = options["layer_code"].strip()
        file_path = options["file"].strip()
        title = options.get("title", "").strip()
        source_layer_name = options.get("source_layer_name", "").strip() or None
        if not layer_code:
            raise CommandError("--layer-code is required")
        if not file_path:
            raise CommandError("--file is required")

        layer, _ = SpatialLayer.objects.update_or_create(
            layer_code=layer_code,
            defaults={
                "title": title or layer_code,
                "name": title or layer_code,
                "slug": layer_code.lower().replace("_", "-"),
                "source_type": SpatialLayerSourceType.UPLOADED_FILE,
                "is_public": False,
                "is_active": True,
            },
        )
        run = ingest_spatial_file(
            layer=layer,
            file_path=file_path,
            source_filename=file_path.split("\\")[-1].split("/")[-1],
            source_layer_name=source_layer_name,
            user=None,
            source_storage_path="",
        )
        if run.status != "succeeded":
            raise CommandError(f"Ingestion failed ({run.run_id}): {run.report_json}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Ingestion succeeded. run_id={run.run_id} layer={layer.layer_code} rows={run.rows_ingested}"
            )
        )
