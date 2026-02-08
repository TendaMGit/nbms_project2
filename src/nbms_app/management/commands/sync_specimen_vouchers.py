from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date

from nbms_app.models import (
    LifecycleStatus,
    QaStatus,
    SensitivityLevel,
    SpecimenVoucher,
    TaxonConcept,
)


def _demo_rows():
    return [
        {
            "institutionCode": "SANBI",
            "collectionCode": "NATIONAL-HERBARIUM",
            "catalogNumber": "NHM-0001",
            "occurrenceID": "ZA-OCC-0001",
            "scientificName": "Aloe ferox",
            "countryCode": "ZA",
            "locality": "Kirstenbosch area",
            "decimalLatitude": "-33.9881",
            "decimalLongitude": "18.4326",
            "eventDate": "2023-03-20",
            "basisOfRecord": "PreservedSpecimen",
        },
        {
            "institutionCode": "SANBI",
            "collectionCode": "NATIONAL-ZOO",
            "catalogNumber": "NZM-0042",
            "occurrenceID": "ZA-OCC-0002",
            "scientificName": "Panthera leo",
            "countryCode": "ZA",
            "locality": "Limpopo province",
            "decimalLatitude": "-23.4012",
            "decimalLongitude": "29.4689",
            "eventDate": "2022-11-05",
            "basisOfRecord": "HumanObservation",
        },
    ]


def _parse_decimal(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except Exception:  # noqa: BLE001
        return None


def _parse_bool(value):
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def _load_rows(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


class Command(BaseCommand):
    help = "Sync specimen/voucher records (Darwin Core style CSV) into TaxonConcept-linked voucher registry."

    def add_arguments(self, parser):
        parser.add_argument("--input", default="", help="CSV file containing DwC voucher rows.")
        parser.add_argument("--seed-demo", action="store_true", help="Use built-in demo records.")

    @transaction.atomic
    def handle(self, *args, **options):
        input_path = (options.get("input") or "").strip()
        seed_demo = bool(options.get("seed_demo"))
        if seed_demo:
            rows = _demo_rows()
        else:
            if not input_path:
                raise CommandError("Provide --input CSV file or use --seed-demo.")
            path = Path(input_path)
            if not path.exists():
                raise CommandError(f"Input file not found: {input_path}")
            rows = _load_rows(path)

        processed = 0
        for row in rows:
            occurrence_id = str(row.get("occurrenceID") or row.get("occurrence_id") or "").strip()
            if not occurrence_id:
                continue

            taxon_code = str(row.get("taxonCode") or row.get("taxon_code") or "").strip()
            scientific_name = str(row.get("scientificName") or row.get("scientific_name") or "").strip()
            taxon = None
            if taxon_code:
                taxon = TaxonConcept.objects.filter(taxon_code=taxon_code).order_by("id").first()
            if taxon is None and scientific_name:
                taxon = TaxonConcept.objects.filter(scientific_name__iexact=scientific_name).order_by("id").first()
            if taxon is None:
                continue

            event_date = parse_date(str(row.get("eventDate") or row.get("event_date") or "").strip())
            if event_date is None and row.get("year"):
                try:
                    event_date = date(int(row.get("year")), 1, 1)
                except Exception:  # noqa: BLE001
                    event_date = None

            sensitivity = str(row.get("sensitivity") or "").strip().lower() or SensitivityLevel.RESTRICTED
            if sensitivity not in SensitivityLevel.values:
                sensitivity = SensitivityLevel.RESTRICTED

            SpecimenVoucher.objects.update_or_create(
                occurrence_id=occurrence_id,
                defaults={
                    "taxon": taxon,
                    "institution_code": str(row.get("institutionCode") or "").strip(),
                    "collection_code": str(row.get("collectionCode") or "").strip(),
                    "catalog_number": str(row.get("catalogNumber") or "").strip(),
                    "basis_of_record": str(row.get("basisOfRecord") or "").strip(),
                    "recorded_by": str(row.get("recordedBy") or "").strip(),
                    "event_date": event_date,
                    "country_code": str(row.get("countryCode") or "ZA").strip()[:2].upper(),
                    "locality": str(row.get("locality") or "").strip(),
                    "decimal_latitude": _parse_decimal(row.get("decimalLatitude")),
                    "decimal_longitude": _parse_decimal(row.get("decimalLongitude")),
                    "coordinate_uncertainty_m": _parse_decimal(row.get("coordinateUncertaintyInMeters")),
                    "has_sensitive_locality": _parse_bool(row.get("has_sensitive_locality")) or sensitivity != SensitivityLevel.PUBLIC,
                    "consent_required": _parse_bool(row.get("consent_required")),
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": sensitivity,
                    "qa_status": QaStatus.VALIDATED,
                    "export_approved": sensitivity == SensitivityLevel.PUBLIC,
                    "source_system": "dwc_voucher_sync",
                    "source_ref": occurrence_id,
                    "organisation": taxon.organisation,
                },
            )
            processed += 1

        for taxon in TaxonConcept.objects.order_by("id"):
            count = taxon.specimen_vouchers.count()
            if taxon.voucher_specimen_count != count or taxon.has_national_voucher_specimen != bool(count):
                taxon.voucher_specimen_count = count
                taxon.has_national_voucher_specimen = bool(count)
                taxon.save(update_fields=["voucher_specimen_count", "has_national_voucher_specimen", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Voucher sync complete. processed={processed}."))
