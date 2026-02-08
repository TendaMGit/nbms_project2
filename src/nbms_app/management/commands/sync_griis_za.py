from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from nbms_app.models import (
    AlienTaxonProfile,
    DwcDegreeOfEstablishment,
    DwcEstablishmentMeans,
    DwcPathwayCategory,
    EICATAssessment,
    EicatCategory,
    IASCountryChecklistRecord,
    LifecycleStatus,
    QaStatus,
    RegistryReviewStatus,
    SEICATAssessment,
    SeicatCategory,
    SensitivityLevel,
    TaxonConcept,
)
from nbms_app.services.registry_catalog import IAS_DEMO_ROWS


def _load_rows(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


def _to_bool(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _normalize_choice(value, choices, default):
    text = str(value or "").strip().lower()
    if text in choices:
        return text
    return default


class Command(BaseCommand):
    help = "Sync South Africa IAS baseline checklist (GRIIS-aligned rows) into IAS registry models."

    def add_arguments(self, parser):
        parser.add_argument("--input", default="", help="CSV path (GRIIS-like columns).")
        parser.add_argument("--seed-demo", action="store_true", help="Use built-in demo GRIIS ZA rows.")
        parser.add_argument("--source-system", default="griis_za")
        parser.add_argument("--source-dataset", default="GRIIS South Africa")

    @transaction.atomic
    def handle(self, *args, **options):
        input_path = (options.get("input") or "").strip()
        seed_demo = bool(options.get("seed_demo"))
        source_system = (options.get("source_system") or "griis_za").strip()
        source_dataset = (options.get("source_dataset") or "GRIIS South Africa").strip()

        if seed_demo:
            rows = list(IAS_DEMO_ROWS)
        else:
            if not input_path:
                raise CommandError("Provide --input CSV path or use --seed-demo.")
            path = Path(input_path)
            if not path.exists():
                raise CommandError(f"Input file not found: {input_path}")
            rows = _load_rows(path)

        processed = 0
        for index, row in enumerate(rows, start=1):
            scientific_name = str(row.get("scientific_name") or row.get("scientificName") or "").strip()
            if not scientific_name:
                continue
            source_identifier = str(row.get("source_identifier") or row.get("recordID") or f"GRIIS-ZA-{index:05d}").strip()
            taxon_code = str(row.get("taxon_code") or f"IAS-TAX-{source_identifier}").strip()

            taxon, _ = TaxonConcept.objects.update_or_create(
                taxon_code=taxon_code,
                defaults={
                    "scientific_name": scientific_name,
                    "canonical_name": str(row.get("canonical_name") or scientific_name).strip(),
                    "taxon_rank": str(row.get("rank") or "species").strip(),
                    "taxonomic_status": str(row.get("taxonomic_status") or "accepted").strip(),
                    "primary_source_system": source_system,
                    "is_native": False,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.VALIDATED,
                    "export_approved": True,
                    "source_system": source_system,
                    "source_ref": source_identifier,
                },
            )

            establishment_code = _normalize_choice(
                row.get("establishment_means_code"),
                set(DwcEstablishmentMeans.values),
                DwcEstablishmentMeans.UNKNOWN,
            )
            degree_code = _normalize_choice(
                row.get("degree_of_establishment_code"),
                set(DwcDegreeOfEstablishment.values),
                DwcDegreeOfEstablishment.UNKNOWN,
            )
            pathway_code = _normalize_choice(
                row.get("pathway_code"),
                set(DwcPathwayCategory.values),
                DwcPathwayCategory.UNKNOWN,
            )

            IASCountryChecklistRecord.objects.update_or_create(
                source_system=source_system,
                source_identifier=source_identifier,
                defaults={
                    "taxon": taxon,
                    "scientific_name": scientific_name,
                    "canonical_name": str(row.get("canonical_name") or scientific_name).strip(),
                    "country_code": str(row.get("country_code") or "ZA").strip().upper()[:2],
                    "source_dataset": source_dataset,
                    "is_alien": _to_bool(row.get("is_alien")) if str(row.get("is_alien", "")).strip() else True,
                    "is_invasive": _to_bool(row.get("is_invasive")),
                    "establishment_means_code": establishment_code,
                    "degree_of_establishment_code": degree_code,
                    "pathway_code": pathway_code,
                    "remarks": str(row.get("remarks") or "").strip(),
                    "retrieved_at": timezone.now(),
                    "payload_json": row,
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.VALIDATED,
                    "export_approved": True,
                    "source_ref": source_identifier,
                },
            )

            profile, _ = AlienTaxonProfile.objects.update_or_create(
                taxon=taxon,
                country_code="ZA",
                defaults={
                    "establishment_means_code": establishment_code,
                    "establishment_means_label": establishment_code.replace("_", " "),
                    "degree_of_establishment_code": degree_code,
                    "degree_of_establishment_label": degree_code.replace("_", " "),
                    "pathway_code": pathway_code,
                    "pathway_label": pathway_code.replace("_", " "),
                    "regulatory_status": str(row.get("regulatory_status") or "unknown").strip(),
                    "is_invasive": _to_bool(row.get("is_invasive")),
                    "notes": str(row.get("notes") or "").strip(),
                    "status": LifecycleStatus.PUBLISHED,
                    "sensitivity": SensitivityLevel.PUBLIC,
                    "qa_status": QaStatus.VALIDATED,
                    "export_approved": True,
                    "source_system": source_system,
                    "source_ref": source_identifier,
                    "organisation": taxon.organisation,
                },
            )

            EICATAssessment.objects.update_or_create(
                profile=profile,
                category=EicatCategory.NE,
                source_system=source_system,
                source_ref=f"{source_identifier}:eicat",
                defaults={
                    "mechanisms_json": [],
                    "impact_scope": "national",
                    "confidence": 0,
                    "uncertainty_notes": "Imported baseline row; assessment pending expert review.",
                    "evidence": "",
                    "review_status": RegistryReviewStatus.NEEDS_REVIEW,
                    "status": LifecycleStatus.DRAFT,
                    "sensitivity": SensitivityLevel.INTERNAL,
                    "qa_status": QaStatus.DRAFT,
                    "export_approved": False,
                },
            )
            SEICATAssessment.objects.update_or_create(
                profile=profile,
                category=SeicatCategory.NE,
                source_system=source_system,
                source_ref=f"{source_identifier}:seicat",
                defaults={
                    "wellbeing_constituents_json": [],
                    "activity_change_narrative": "",
                    "confidence": 0,
                    "uncertainty_notes": "Imported baseline row; assessment pending expert review.",
                    "evidence": "",
                    "review_status": RegistryReviewStatus.NEEDS_REVIEW,
                    "status": LifecycleStatus.DRAFT,
                    "sensitivity": SensitivityLevel.INTERNAL,
                    "qa_status": QaStatus.DRAFT,
                    "export_approved": False,
                },
            )
            processed += 1

        self.stdout.write(self.style.SUCCESS(f"GRIIS ZA sync complete. processed={processed}."))
