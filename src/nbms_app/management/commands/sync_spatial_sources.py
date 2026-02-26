from __future__ import annotations

from django.core.management.base import BaseCommand

from nbms_app.services.spatial_sources import sync_spatial_sources


class Command(BaseCommand):
    help = "Sync configured spatial sources into SpatialLayer/SpatialFeature with provenance and checksums."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-code",
            action="append",
            dest="source_codes",
            default=[],
            help="Restrict sync to one or more SpatialSource codes.",
        )
        parser.add_argument(
            "--include-optional",
            action="store_true",
            help="Include sources not enabled by default (for token-gated integrations).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-ingestion even when checksum is unchanged.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate selection but do not download/ingest.",
        )
        parser.add_argument(
            "--no-seed-defaults",
            action="store_true",
            help="Do not upsert default source registry entries before syncing.",
        )

    def handle(self, *args, **options):
        summary = sync_spatial_sources(
            actor=None,
            source_codes=options.get("source_codes") or None,
            include_optional=bool(options.get("include_optional")),
            force=bool(options.get("force")),
            dry_run=bool(options.get("dry_run")),
            seed_defaults=not bool(options.get("no_seed_defaults")),
        )

        rows = summary["results"]
        self.stdout.write("| source_code | layer_code | status | rows_ingested | checksum | run_id | detail |")
        self.stdout.write("|---|---|---|---:|---|---|---|")
        for row in rows:
            self.stdout.write(
                "| {source_code} | {layer_code} | {status} | {rows_ingested} | {checksum} | {run_id} | {detail} |".format(
                    source_code=row.get("source_code", ""),
                    layer_code=row.get("layer_code", ""),
                    status=row.get("status", ""),
                    rows_ingested=row.get("rows_ingested", 0),
                    checksum=row.get("checksum", ""),
                    run_id=row.get("run_id", ""),
                    detail=(row.get("detail", "") or "").replace("\n", " ").replace("|", "/"),
                )
            )

        counts = summary.get("status_counts", {})
        self.stdout.write(
            self.style.SUCCESS(
                "Spatial source sync finished "
                f"(ready={counts.get('ready', 0)}, skipped={counts.get('skipped', 0)}, "
                f"blocked={counts.get('blocked', 0)}, failed={counts.get('failed', 0)})."
            )
        )
