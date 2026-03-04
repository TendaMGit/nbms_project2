from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nbms_app.services.nba_pilot_ingest import DEFAULT_MANIFEST_PATH, ingest_manifest


class Command(BaseCommand):
    help = "Ingest pinned NBA pilot workflow outputs into datasets, releases, and indicator series."

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            default=str(DEFAULT_MANIFEST_PATH),
            help="Path to the pilot ingest manifest YAML.",
        )
        parser.add_argument(
            "--log-file",
            default="media/ingest_reports/nba_pilot_v1.json",
            help="Where to write the ingest JSON report.",
        )

    def handle(self, *args, **options):
        manifest_path = options["manifest"]
        log_path = Path(options["log_file"])
        log_path.parent.mkdir(parents=True, exist_ok=True)

        report = ingest_manifest(manifest_path=manifest_path, stdout=self.stdout)
        log_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.stdout.write(f"[pilot] report written to {log_path}")

        if report["errors"]:
            raise CommandError(
                f"Pilot ingest completed with {len(report['errors'])} failures. See {log_path} for details."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Pilot ingest succeeded for {len(report['entries'])} indicators using {manifest_path}."
            )
        )
