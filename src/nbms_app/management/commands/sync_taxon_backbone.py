from __future__ import annotations

import csv
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from nbms_app.models import (
    LifecycleStatus,
    Organisation,
    QaStatus,
    SensitivityLevel,
    TaxonConcept,
    TaxonName,
    TaxonNameType,
    TaxonSourceRecord,
)
from nbms_app.services.registry_catalog import TAXON_DEMO_ROWS


def _load_rows(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("rows") or payload.get("taxa") or []
        if not isinstance(payload, list):
            raise CommandError("JSON input must be a list of taxon rows.")
        return payload

    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


def _safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _species_match(name: str) -> dict:
    query = urllib.parse.urlencode({"name": name})
    url = f"https://api.gbif.org/v1/species/match?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "NBMS-TaxonSync/1.0"}, method="GET")
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


class Command(BaseCommand):
    help = "Sync taxon backbone records from CSV/JSON and enrich with GBIF species match responses."

    def add_arguments(self, parser):
        parser.add_argument("--input", default="", help="Path to CSV/JSON rows.")
        parser.add_argument("--skip-remote", action="store_true", help="Skip GBIF match API lookup.")
        parser.add_argument("--seed-demo", action="store_true", help="Use built-in demo rows.")
        parser.add_argument("--source-system", default="nbms_taxon_sync")

    @transaction.atomic
    def handle(self, *args, **options):
        input_path = _safe_text(options.get("input"))
        seed_demo = bool(options.get("seed_demo"))
        skip_remote = bool(options.get("skip_remote"))
        source_system = _safe_text(options.get("source_system")) or "nbms_taxon_sync"

        if seed_demo:
            rows = list(TAXON_DEMO_ROWS)
        else:
            if not input_path:
                raise CommandError("Provide --input path or use --seed-demo.")
            path = Path(input_path)
            if not path.exists():
                raise CommandError(f"Input file does not exist: {input_path}")
            rows = _load_rows(path)

        sanbi, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute", "org_type": "Government"},
        )

        created_or_updated = 0
        source_rows = 0
        for index, row in enumerate(rows, start=1):
            scientific_name = _safe_text(row.get("scientific_name") or row.get("name"))
            if not scientific_name:
                continue
            taxon_code = _safe_text(row.get("taxon_code")) or f"NBMS-TAXON-{index:05d}"
            rank = _safe_text(row.get("taxon_rank") or row.get("rank"))

            match_payload = {}
            if not skip_remote:
                try:
                    match_payload = _species_match(scientific_name)
                except Exception as exc:  # noqa: BLE001
                    match_payload = {"error": str(exc)}

            taxon_defaults = {
                "scientific_name": scientific_name,
                "canonical_name": _safe_text(row.get("canonical_name") or match_payload.get("canonicalName") or scientific_name),
                "taxon_rank": rank or _safe_text(match_payload.get("rank")),
                "taxonomic_status": _safe_text(row.get("taxonomic_status") or match_payload.get("status")),
                "kingdom": _safe_text(row.get("kingdom") or match_payload.get("kingdom")),
                "phylum": _safe_text(row.get("phylum") or match_payload.get("phylum")),
                "class_name": _safe_text(row.get("class") or row.get("class_name") or match_payload.get("class")),
                "order": _safe_text(row.get("order") or match_payload.get("order")),
                "family": _safe_text(row.get("family") or match_payload.get("family")),
                "genus": _safe_text(row.get("genus") or match_payload.get("genus")),
                "species": _safe_text(row.get("species") or match_payload.get("species")),
                "gbif_taxon_key": match_payload.get("speciesKey") or match_payload.get("usageKey"),
                "gbif_usage_key": match_payload.get("usageKey"),
                "gbif_accepted_taxon_key": match_payload.get("acceptedUsageKey"),
                "primary_source_system": "gbif_species_match" if match_payload and not match_payload.get("error") else source_system,
                "is_native": row.get("is_native") if row.get("is_native") in {True, False} else None,
                "is_endemic": bool(row.get("is_endemic")) if str(row.get("is_endemic", "")).strip() != "" else False,
                "organisation": sanbi,
                "status": LifecycleStatus.PUBLISHED,
                "sensitivity": SensitivityLevel.PUBLIC,
                "qa_status": QaStatus.VALIDATED,
                "export_approved": True,
                "source_system": source_system,
                "source_ref": taxon_code,
            }
            taxon, _ = TaxonConcept.objects.update_or_create(taxon_code=taxon_code, defaults=taxon_defaults)
            created_or_updated += 1

            TaxonName.objects.update_or_create(
                taxon=taxon,
                name=scientific_name,
                name_type=TaxonNameType.ACCEPTED,
                language="la",
                defaults={
                    "is_preferred": True,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "source_system": source_system,
                    "source_ref": taxon_code,
                },
            )
            vernacular = _safe_text(row.get("vernacular_name") or row.get("common_name"))
            if vernacular:
                TaxonName.objects.update_or_create(
                    taxon=taxon,
                    name=vernacular,
                    name_type=TaxonNameType.VERNACULAR,
                    language=_safe_text(row.get("language")) or "en",
                    defaults={
                        "is_preferred": True,
                        "status": LifecycleStatus.PUBLISHED,
                        "sensitivity": SensitivityLevel.PUBLIC,
                        "source_system": source_system,
                        "source_ref": taxon_code,
                    },
                )

            payload = {"input": row, "gbif_match": match_payload}
            payload_text = json.dumps(payload, sort_keys=True)
            TaxonSourceRecord.objects.update_or_create(
                taxon=taxon,
                source_system="gbif_species_match" if match_payload else source_system,
                source_ref=taxon_code,
                defaults={
                    "source_url": "https://api.gbif.org/v1/species/match",
                    "retrieved_at": timezone.now(),
                    "payload_json": payload,
                    "payload_hash": hashlib.sha256(payload_text.encode("utf-8")).hexdigest(),
                    "licence": "GBIF data use policy",
                    "citation": "GBIF species match endpoint",
                    "is_primary": True,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.VALIDATED,
                    "export_approved": True,
                    "organisation": sanbi,
                },
            )
            source_rows += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Taxon backbone sync complete. taxon_rows={created_or_updated} source_records={source_rows}."
            )
        )
