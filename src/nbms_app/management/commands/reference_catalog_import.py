import csv
import json
import re
from datetime import date
from pathlib import Path
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from nbms_app.models import (
    AccessLevel,
    AgreementType,
    DataAgreement,
    DatasetCatalog,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkIndicatorType,
    FrameworkTarget,
    Indicator,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    Methodology,
    MethodologyDatasetLink,
    MethodologyIndicatorLink,
    MethodologyStatus,
    MethodologyVersion,
    MonitoringProgramme,
    Organisation,
    ProgrammeDatasetLink,
    ProgrammeIndicatorLink,
    ProgrammeType,
    QaStatus,
    RelationshipType,
    SensitivityClass,
    SensitivityLevel,
    UpdateFrequency,
)


ENTITY_HEADERS = {
    "organisation": [
        "org_uuid",
        "org_code",
        "org_name",
        "org_type",
        "parent_org_code",
        "website_url",
        "primary_contact_name",
        "primary_contact_email",
        "alternative_contact_name",
        "alternative_contact_email",
        "notes",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "sensitivity_class": [
        "sensitivity_code",
        "sensitivity_name",
        "description",
        "access_level_default",
        "consent_required_default",
        "redaction_policy",
        "legal_basis",
        "notes",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "data_agreement": [
        "agreement_uuid",
        "agreement_code",
        "title",
        "agreement_type",
        "parties_org_codes",
        "start_date",
        "end_date",
        "status",
        "licence",
        "restrictions_summary",
        "benefit_sharing_terms",
        "citation_requirement",
        "document_url",
        "primary_contact_name",
        "primary_contact_email",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "framework": [
        "framework_uuid",
        "framework_code",
        "title",
        "description",
        "organisation_code",
        "status",
        "sensitivity",
        "review_note",
    ],
    "monitoring_programme": [
        "programme_uuid",
        "programme_code",
        "title",
        "description",
        "programme_type",
        "lead_org_code",
        "partner_org_codes",
        "start_year",
        "end_year",
        "geographic_scope",
        "spatial_coverage_description",
        "taxonomic_scope",
        "ecosystem_scope",
        "objectives",
        "sampling_design_summary",
        "update_frequency",
        "qa_process_summary",
        "sensitivity_code",
        "consent_required",
        "agreement_code",
        "website_url",
        "primary_contact_name",
        "primary_contact_email",
        "alternative_contact_name",
        "alternative_contact_email",
        "is_active",
        "source_system",
        "source_ref",
        "notes",
    ],
    "dataset_catalog": [
        "dataset_uuid",
        "dataset_code",
        "title",
        "description",
        "dataset_type",
        "custodian_org_code",
        "producer_org_code",
        "licence",
        "access_level",
        "sensitivity_code",
        "consent_required",
        "agreement_code",
        "temporal_start",
        "temporal_end",
        "update_frequency",
        "spatial_coverage_description",
        "spatial_resolution",
        "taxonomy_standard",
        "ecosystem_classification",
        "doi_or_identifier",
        "landing_page_url",
        "api_endpoint_url",
        "file_formats",
        "qa_status",
        "citation",
        "keywords",
        "last_updated_date",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "methodology": [
        "methodology_uuid",
        "methodology_code",
        "title",
        "description",
        "owner_org_code",
        "scope",
        "references_url",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "methodology_version": [
        "methodology_version_uuid",
        "methodology_code",
        "version",
        "status",
        "effective_date",
        "deprecated_date",
        "change_log",
        "protocol_url",
        "computational_script_url",
        "parameters_json",
        "qa_steps_summary",
        "peer_reviewed",
        "approval_body",
        "approval_reference",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "programme_dataset_link": [
        "programme_code",
        "programme_uuid",
        "dataset_code",
        "dataset_uuid",
        "relationship_type",
        "role",
        "notes",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "programme_indicator_link": [
        "programme_code",
        "programme_uuid",
        "indicator_code",
        "indicator_uuid",
        "relationship_type",
        "role",
        "notes",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "methodology_dataset_link": [
        "methodology_code",
        "methodology_uuid",
        "dataset_code",
        "dataset_uuid",
        "relationship_type",
        "role",
        "notes",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "methodology_indicator_link": [
        "methodology_code",
        "methodology_uuid",
        "indicator_code",
        "indicator_uuid",
        "relationship_type",
        "role",
        "notes",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "gbf_goals": [
        "framework_code",
        "goal_code",
        "goal_title",
        "official_text",
        "description",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "gbf_targets": [
        "framework_code",
        "target_code",
        "goal_code",
        "target_title",
        "official_text",
        "description",
        "is_active",
        "source_system",
        "source_ref",
    ],
    "gbf_indicators": [
        "framework_code",
        "framework_target_code",
        "indicator_code",
        "indicator_title",
        "indicator_type",
        "description",
        "is_active",
        "source_system",
        "source_ref",
    ],
}

ENTITY_HEADERS["framework_goal"] = ENTITY_HEADERS["gbf_goals"]
ENTITY_HEADERS["framework_target"] = ENTITY_HEADERS["gbf_targets"]
ENTITY_HEADERS["framework_indicator"] = ENTITY_HEADERS["gbf_indicators"]

CONTROLLED_VOCABS = {
    "access_level": {choice.value for choice in AccessLevel},
    "update_frequency": {choice.value for choice in UpdateFrequency},
    "qa_status": {choice.value for choice in QaStatus},
    "agreement_type": {choice.value for choice in AgreementType},
    "programme_type": {choice.value for choice in ProgrammeType},
    "relationship_type": {choice.value for choice in RelationshipType},
    "methodology_status": {choice.value for choice in MethodologyStatus},
    "framework_indicator_type": {choice.value for choice in FrameworkIndicatorType},
    "lifecycle_status": {choice.value for choice in LifecycleStatus},
    "sensitivity_level": {choice.value for choice in SensitivityLevel},
    "licence_type": {"CC-BY", "CC-BY-SA", "CC0", "custom", "restricted"},
}


class Command(BaseCommand):
    help = "Import reference catalog entities from CSV templates."

    def add_arguments(self, parser):
        parser.add_argument("--entity", required=True, choices=sorted(ENTITY_HEADERS.keys()))
        parser.add_argument("--file", required=True, help="Path to input CSV file.")
        parser.add_argument("--mode", choices=["upsert", "insert_only"], default="upsert")
        parser.add_argument("--dry-run", action="store_true", help="Validate and simulate without writing to the DB.")
        parser.add_argument("--strict", action="store_true", help="Fail on first error.")

    def handle(self, *args, **options):
        entity = options["entity"]
        csv_path = Path(options["file"])
        mode = options["mode"]
        dry_run = options["dry_run"]
        strict = options["strict"]

        if not csv_path.exists():
            raise CommandError(f"Input file not found: {csv_path}")

        import_fn = _IMPORTERS.get(entity)
        if not import_fn:
            raise CommandError(f"Unsupported entity: {entity}")

        created = 0
        updated = 0
        errors = []

        def run_import():
            nonlocal created, updated
            with csv_path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                _ensure_headers(reader, entity)
                for row_number, row in enumerate(reader, start=2):
                    try:
                        if not strict and not dry_run:
                            with transaction.atomic():
                                c, u = import_fn(row, mode, row_number)
                        else:
                            c, u = import_fn(row, mode, row_number)
                    except CommandError as exc:
                        if strict:
                            raise
                        errors.append(f"Row {row_number}: {exc}")
                        continue
                    created += c
                    updated += u

        if dry_run or strict:
            with transaction.atomic():
                run_import()
                if dry_run:
                    transaction.set_rollback(True)
        else:
            run_import()

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            self.stdout.write(
                self.style.WARNING(
                    f"Import completed with {len(errors)} error(s). Created: {created}, Updated: {updated}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Import complete. Created: {created}, Updated: {updated}.")
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no changes were committed."))



def _ensure_headers(reader, entity):
    expected = ENTITY_HEADERS[entity]
    fieldnames = reader.fieldnames or []
    missing = [name for name in expected if name not in fieldnames]
    if missing:
        raise CommandError(f"Missing required columns: {', '.join(missing)}")


def _clean(value):
    return (value or "").strip()


def _parse_uuid(value, field, row_number):
    value = _clean(value)
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise CommandError(f"Row {row_number}: invalid UUID in {field}: {value}") from exc


def _parse_date(value, field, row_number):
    value = _clean(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CommandError(f"Row {row_number}: invalid date in {field}: {value}") from exc


def _parse_int(value, field, row_number):
    value = _clean(value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise CommandError(f"Row {row_number}: invalid integer in {field}: {value}") from exc


def _parse_bool(value, field, row_number, default=None):
    if value is None:
        return default
    value = str(value).strip().lower()
    if not value:
        return default
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    raise CommandError(f"Row {row_number}: invalid boolean in {field}: {value}")


def _parse_json(value, field, row_number):
    value = _clean(value)
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CommandError(f"Row {row_number}: invalid JSON in {field}: {exc}") from exc


def _split_codes(value):
    value = _clean(value)
    if not value:
        return []
    parts = re.split(r"[;,|]", value)
    return [part.strip() for part in parts if part.strip()]


def _normalize_choice(value, allowed, field, row_number, default=""):
    value = _clean(value)
    if not value:
        return default
    allowed_map = {item.lower(): item for item in allowed}
    normalized = allowed_map.get(value.lower())
    if not normalized:
        raise CommandError(f"Row {row_number}: invalid {field}: {value}")
    return normalized


def _check_uuid_conflict(model, uuid_value, code_field, code_value, row_number, label):
    if not uuid_value or not code_value:
        return
    existing = model.objects.filter(**{code_field: code_value}).first()
    if existing and existing.uuid != uuid_value:
        raise CommandError(
            f"Row {row_number}: {label} code '{code_value}' already exists with a different UUID."
        )


def _resolve_by_code(model, code_field, code_value, row_number, label):
    code_value = _clean(code_value)
    if not code_value:
        return None
    obj = model.objects.filter(**{code_field: code_value}).first()
    if not obj:
        raise CommandError(f"Row {row_number}: {label} not found for code '{code_value}'.")
    return obj


def _resolve_by_uuid_or_code(model, uuid_value, code_value, code_field, row_number, label):
    if uuid_value:
        obj = model.objects.filter(uuid=uuid_value).first()
        if not obj:
            raise CommandError(f"Row {row_number}: {label} UUID not found: {uuid_value}")
        return obj
    code_value = _clean(code_value)
    if code_value:
        obj = model.objects.filter(**{code_field: code_value}).first()
        if not obj:
            raise CommandError(f"Row {row_number}: {label} not found for code '{code_value}'.")
        return obj
    raise CommandError(f"Row {row_number}: {label} requires {code_field} or UUID.")


def _upsert_model(model, lookup, defaults, mode, row_number, label):
    if mode == "insert_only":
        if model.objects.filter(**lookup).exists():
            raise CommandError(f"Row {row_number}: {label} already exists.")
        try:
            obj = model.objects.create(**lookup, **defaults)
        except IntegrityError as exc:
            raise CommandError(f"Row {row_number}: {label} violates a constraint.") from exc
        return obj, 1, 0
    try:
        obj, created = model.objects.update_or_create(defaults=defaults, **lookup)
    except IntegrityError as exc:
        raise CommandError(f"Row {row_number}: {label} violates a constraint.") from exc
    return obj, (1 if created else 0), (0 if created else 1)



def _import_organisation(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("org_uuid"), "org_uuid", row_number)
    org_code = _clean(row.get("org_code"))
    name = _clean(row.get("org_name"))
    if not name:
        raise CommandError("org_name is required.")
    if not uuid_value and not org_code:
        raise CommandError("org_uuid or org_code is required.")
    _check_uuid_conflict(Organisation, uuid_value, "org_code", org_code, row_number, "Organisation")

    parent_org = _resolve_by_code(Organisation, "org_code", row.get("parent_org_code"), row_number, "Parent org")
    defaults = {
        "name": name,
        "org_code": org_code or None,
        "org_type": _clean(row.get("org_type")),
        "parent_org": parent_org,
        "website_url": _clean(row.get("website_url")),
        "primary_contact_name": _clean(row.get("primary_contact_name")),
        "primary_contact_email": _clean(row.get("primary_contact_email")),
        "alternative_contact_name": _clean(row.get("alternative_contact_name")),
        "alternative_contact_email": _clean(row.get("alternative_contact_email")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    lookup = {"uuid": uuid_value} if uuid_value else {"org_code": org_code}
    _, created, updated = _upsert_model(Organisation, lookup, defaults, mode, row_number, "Organisation")
    return created, updated


def _import_sensitivity_class(row, mode, row_number):
    code = _clean(row.get("sensitivity_code"))
    name = _clean(row.get("sensitivity_name"))
    if not code or not name:
        raise CommandError("sensitivity_code and sensitivity_name are required.")
    access_level = _normalize_choice(
        row.get("access_level_default"),
        CONTROLLED_VOCABS["access_level"],
        "access_level_default",
        row_number,
        default=AccessLevel.INTERNAL,
    )
    defaults = {
        "sensitivity_name": name,
        "description": _clean(row.get("description")),
        "access_level_default": access_level,
        "consent_required_default": _parse_bool(
            row.get("consent_required_default"),
            "consent_required_default",
            row_number,
            default=False,
        ),
        "redaction_policy": _clean(row.get("redaction_policy")),
        "legal_basis": _clean(row.get("legal_basis")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        SensitivityClass,
        {"sensitivity_code": code},
        defaults,
        mode,
        row_number,
        "SensitivityClass",
    )
    return created, updated


def _import_data_agreement(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("agreement_uuid"), "agreement_uuid", row_number)
    code = _clean(row.get("agreement_code"))
    title = _clean(row.get("title"))
    if not title:
        raise CommandError("title is required.")
    if not code:
        raise CommandError("agreement_code is required.")
    _check_uuid_conflict(DataAgreement, uuid_value, "agreement_code", code, row_number, "DataAgreement")

    agreement_type = _normalize_choice(
        row.get("agreement_type"),
        CONTROLLED_VOCABS["agreement_type"],
        "agreement_type",
        row_number,
        default="",
    )
    licence = _clean(row.get("licence"))
    if licence:
        licence = _normalize_choice(licence, CONTROLLED_VOCABS["licence_type"], "licence", row_number, default=licence)

    defaults = {
        "agreement_code": code or None,
        "title": title,
        "agreement_type": agreement_type,
        "status": _clean(row.get("status")),
        "start_date": _parse_date(row.get("start_date"), "start_date", row_number),
        "end_date": _parse_date(row.get("end_date"), "end_date", row_number),
        "licence": licence,
        "restrictions_summary": _clean(row.get("restrictions_summary")),
        "benefit_sharing_terms": _clean(row.get("benefit_sharing_terms")),
        "citation_requirement": _clean(row.get("citation_requirement")),
        "document_url": _clean(row.get("document_url")),
        "primary_contact_name": _clean(row.get("primary_contact_name")),
        "primary_contact_email": _clean(row.get("primary_contact_email")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    lookup = {"uuid": uuid_value} if uuid_value else {"agreement_code": code}
    agreement, created, updated = _upsert_model(
        DataAgreement,
        lookup,
        defaults,
        mode,
        row_number,
        "DataAgreement",
    )

    party_codes = _split_codes(row.get("parties_org_codes"))
    parties = []
    for code_value in party_codes:
        org = _resolve_by_code(Organisation, "org_code", code_value, row_number, "Organisation")
        parties.append(org)
    agreement.parties.set(parties)
    return created, updated


def _import_framework(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("framework_uuid"), "framework_uuid", row_number)
    code = _clean(row.get("framework_code"))
    title = _clean(row.get("title"))
    if not code or not title:
        raise CommandError("framework_code and title are required.")
    _check_uuid_conflict(Framework, uuid_value, "code", code, row_number, "Framework")

    organisation = _resolve_by_code(
        Organisation,
        "org_code",
        row.get("organisation_code"),
        row_number,
        "Organisation",
    )
    status = _normalize_choice(
        row.get("status"),
        CONTROLLED_VOCABS["lifecycle_status"],
        "status",
        row_number,
        default=LifecycleStatus.PUBLISHED,
    )
    sensitivity = _normalize_choice(
        row.get("sensitivity"),
        CONTROLLED_VOCABS["sensitivity_level"],
        "sensitivity",
        row_number,
        default=SensitivityLevel.PUBLIC,
    )

    defaults = {
        "code": code,
        "title": title,
        "description": _clean(row.get("description")),
        "organisation": organisation,
        "status": status,
        "sensitivity": sensitivity,
        "review_note": _clean(row.get("review_note")),
    }
    lookup = {"uuid": uuid_value} if uuid_value else {"code": code}
    _, created, updated = _upsert_model(
        Framework,
        lookup,
        defaults,
        mode,
        row_number,
        "Framework",
    )
    return created, updated


def _import_monitoring_programme(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("programme_uuid"), "programme_uuid", row_number)
    code = _clean(row.get("programme_code"))
    title = _clean(row.get("title"))
    if not title:
        raise CommandError("title is required.")
    if not code:
        raise CommandError("programme_code is required.")
    _check_uuid_conflict(
        MonitoringProgramme,
        uuid_value,
        "programme_code",
        code,
        row_number,
        "MonitoringProgramme",
    )

    programme_type = _normalize_choice(
        row.get("programme_type"),
        CONTROLLED_VOCABS["programme_type"],
        "programme_type",
        row_number,
        default="",
    )
    update_frequency = _normalize_choice(
        row.get("update_frequency"),
        CONTROLLED_VOCABS["update_frequency"],
        "update_frequency",
        row_number,
        default="",
    )
    sensitivity = _resolve_by_code(
        SensitivityClass,
        "sensitivity_code",
        row.get("sensitivity_code"),
        row_number,
        "SensitivityClass",
    )
    agreement = _resolve_by_code(
        DataAgreement,
        "agreement_code",
        row.get("agreement_code"),
        row_number,
        "DataAgreement",
    )
    lead_org = _resolve_by_code(Organisation, "org_code", row.get("lead_org_code"), row_number, "Organisation")

    defaults = {
        "programme_code": code or None,
        "title": title,
        "description": _clean(row.get("description")),
        "programme_type": programme_type,
        "lead_org": lead_org,
        "start_year": _parse_int(row.get("start_year"), "start_year", row_number),
        "end_year": _parse_int(row.get("end_year"), "end_year", row_number),
        "geographic_scope": _clean(row.get("geographic_scope")),
        "spatial_coverage_description": _clean(row.get("spatial_coverage_description")),
        "taxonomic_scope": _clean(row.get("taxonomic_scope")),
        "ecosystem_scope": _clean(row.get("ecosystem_scope")),
        "objectives": _clean(row.get("objectives")),
        "sampling_design_summary": _clean(row.get("sampling_design_summary")),
        "update_frequency": update_frequency,
        "qa_process_summary": _clean(row.get("qa_process_summary")),
        "sensitivity_class": sensitivity,
        "consent_required": _parse_bool(row.get("consent_required"), "consent_required", row_number, default=False),
        "agreement": agreement,
        "website_url": _clean(row.get("website_url")),
        "primary_contact_name": _clean(row.get("primary_contact_name")),
        "primary_contact_email": _clean(row.get("primary_contact_email")),
        "alternative_contact_name": _clean(row.get("alternative_contact_name")),
        "alternative_contact_email": _clean(row.get("alternative_contact_email")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    lookup = {"uuid": uuid_value} if uuid_value else {"programme_code": code}
    programme, created, updated = _upsert_model(
        MonitoringProgramme,
        lookup,
        defaults,
        mode,
        row_number,
        "MonitoringProgramme",
    )

    partner_codes = _split_codes(row.get("partner_org_codes"))
    partners = []
    for code_value in partner_codes:
        org = _resolve_by_code(Organisation, "org_code", code_value, row_number, "Organisation")
        partners.append(org)
    programme.partners.set(partners)
    return created, updated


def _import_dataset_catalog(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("dataset_uuid"), "dataset_uuid", row_number)
    code = _clean(row.get("dataset_code"))
    title = _clean(row.get("title"))
    if not title:
        raise CommandError("title is required.")
    if not code:
        raise CommandError("dataset_code is required.")
    _check_uuid_conflict(DatasetCatalog, uuid_value, "dataset_code", code, row_number, "DatasetCatalog")

    access_level = _normalize_choice(
        row.get("access_level"),
        CONTROLLED_VOCABS["access_level"],
        "access_level",
        row_number,
        default=AccessLevel.INTERNAL,
    )
    update_frequency = _normalize_choice(
        row.get("update_frequency"),
        CONTROLLED_VOCABS["update_frequency"],
        "update_frequency",
        row_number,
        default="",
    )
    qa_status = _normalize_choice(
        row.get("qa_status"),
        CONTROLLED_VOCABS["qa_status"],
        "qa_status",
        row_number,
        default="",
    )
    licence = _clean(row.get("licence"))
    if licence:
        licence = _normalize_choice(licence, CONTROLLED_VOCABS["licence_type"], "licence", row_number, default=licence)

    custodian_org = _resolve_by_code(
        Organisation,
        "org_code",
        row.get("custodian_org_code"),
        row_number,
        "Organisation",
    )
    producer_org = _resolve_by_code(
        Organisation,
        "org_code",
        row.get("producer_org_code"),
        row_number,
        "Organisation",
    )
    sensitivity = _resolve_by_code(
        SensitivityClass,
        "sensitivity_code",
        row.get("sensitivity_code"),
        row_number,
        "SensitivityClass",
    )
    agreement = _resolve_by_code(
        DataAgreement,
        "agreement_code",
        row.get("agreement_code"),
        row_number,
        "DataAgreement",
    )

    defaults = {
        "dataset_code": code or None,
        "title": title,
        "description": _clean(row.get("description")),
        "dataset_type": _clean(row.get("dataset_type")),
        "custodian_org": custodian_org,
        "producer_org": producer_org,
        "licence": licence,
        "access_level": access_level,
        "sensitivity_class": sensitivity,
        "consent_required": _parse_bool(row.get("consent_required"), "consent_required", row_number, default=False),
        "agreement": agreement,
        "temporal_start": _parse_date(row.get("temporal_start"), "temporal_start", row_number),
        "temporal_end": _parse_date(row.get("temporal_end"), "temporal_end", row_number),
        "update_frequency": update_frequency,
        "spatial_coverage_description": _clean(row.get("spatial_coverage_description")),
        "spatial_resolution": _clean(row.get("spatial_resolution")),
        "taxonomy_standard": _clean(row.get("taxonomy_standard")),
        "ecosystem_classification": _clean(row.get("ecosystem_classification")),
        "doi_or_identifier": _clean(row.get("doi_or_identifier")),
        "landing_page_url": _clean(row.get("landing_page_url")),
        "api_endpoint_url": _clean(row.get("api_endpoint_url")),
        "file_formats": _clean(row.get("file_formats")),
        "qa_status": qa_status,
        "citation": _clean(row.get("citation")),
        "keywords": _clean(row.get("keywords")),
        "last_updated_date": _parse_date(row.get("last_updated_date"), "last_updated_date", row_number),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    lookup = {"uuid": uuid_value} if uuid_value else {"dataset_code": code}
    _, created, updated = _upsert_model(
        DatasetCatalog,
        lookup,
        defaults,
        mode,
        row_number,
        "DatasetCatalog",
    )
    return created, updated



def _import_methodology(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("methodology_uuid"), "methodology_uuid", row_number)
    code = _clean(row.get("methodology_code"))
    title = _clean(row.get("title"))
    if not title:
        raise CommandError("title is required.")
    if not code:
        raise CommandError("methodology_code is required.")
    _check_uuid_conflict(Methodology, uuid_value, "methodology_code", code, row_number, "Methodology")

    owner_org = _resolve_by_code(Organisation, "org_code", row.get("owner_org_code"), row_number, "Organisation")
    defaults = {
        "methodology_code": code or None,
        "title": title,
        "description": _clean(row.get("description")),
        "owner_org": owner_org,
        "scope": _clean(row.get("scope")),
        "references_url": _clean(row.get("references_url")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    lookup = {"uuid": uuid_value} if uuid_value else {"methodology_code": code}
    _, created, updated = _upsert_model(
        Methodology,
        lookup,
        defaults,
        mode,
        row_number,
        "Methodology",
    )
    return created, updated


def _import_methodology_version(row, mode, row_number):
    uuid_value = _parse_uuid(row.get("methodology_version_uuid"), "methodology_version_uuid", row_number)
    methodology_code = _clean(row.get("methodology_code"))
    version = _clean(row.get("version"))
    if not methodology_code or not version:
        raise CommandError("methodology_code and version are required.")
    methodology = _resolve_by_code(Methodology, "methodology_code", methodology_code, row_number, "Methodology")
    if uuid_value:
        existing = MethodologyVersion.objects.filter(uuid=uuid_value).first()
        if existing and (existing.methodology_id != methodology.id or existing.version != version):
            raise CommandError("methodology_version_uuid does not match methodology_code/version.")
        conflict = MethodologyVersion.objects.filter(methodology=methodology, version=version).first()
        if conflict and conflict.uuid != uuid_value:
            raise CommandError("methodology_code/version already exists with a different UUID.")

    status = _normalize_choice(
        row.get("status"),
        CONTROLLED_VOCABS["methodology_status"],
        "status",
        row_number,
        default=MethodologyStatus.DRAFT,
    )

    defaults = {
        "methodology": methodology,
        "version": version,
        "status": status,
        "effective_date": _parse_date(row.get("effective_date"), "effective_date", row_number),
        "deprecated_date": _parse_date(row.get("deprecated_date"), "deprecated_date", row_number),
        "change_log": _clean(row.get("change_log")),
        "protocol_url": _clean(row.get("protocol_url")),
        "computational_script_url": _clean(row.get("computational_script_url")),
        "parameters_json": _parse_json(row.get("parameters_json"), "parameters_json", row_number),
        "qa_steps_summary": _clean(row.get("qa_steps_summary")),
        "peer_reviewed": _parse_bool(row.get("peer_reviewed"), "peer_reviewed", row_number, default=False),
        "approval_body": _clean(row.get("approval_body")),
        "approval_reference": _clean(row.get("approval_reference")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }

    lookup = {"uuid": uuid_value} if uuid_value else {"methodology": methodology, "version": version}
    _, created, updated = _upsert_model(
        MethodologyVersion,
        lookup,
        defaults,
        mode,
        row_number,
        "MethodologyVersion",
    )
    return created, updated



def _import_programme_dataset_link(row, mode, row_number):
    programme = _resolve_by_uuid_or_code(
        MonitoringProgramme,
        _parse_uuid(row.get("programme_uuid"), "programme_uuid", row_number),
        row.get("programme_code"),
        "programme_code",
        row_number,
        "MonitoringProgramme",
    )
    dataset = _resolve_by_uuid_or_code(
        DatasetCatalog,
        _parse_uuid(row.get("dataset_uuid"), "dataset_uuid", row_number),
        row.get("dataset_code"),
        "dataset_code",
        row_number,
        "DatasetCatalog",
    )
    relationship_type = _normalize_choice(
        row.get("relationship_type"),
        CONTROLLED_VOCABS["relationship_type"],
        "relationship_type",
        row_number,
        default="",
    )
    defaults = {
        "relationship_type": relationship_type,
        "role": _clean(row.get("role")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        ProgrammeDatasetLink,
        {"programme": programme, "dataset": dataset},
        defaults,
        mode,
        row_number,
        "ProgrammeDatasetLink",
    )
    return created, updated


def _import_programme_indicator_link(row, mode, row_number):
    programme = _resolve_by_uuid_or_code(
        MonitoringProgramme,
        _parse_uuid(row.get("programme_uuid"), "programme_uuid", row_number),
        row.get("programme_code"),
        "programme_code",
        row_number,
        "MonitoringProgramme",
    )
    indicator = _resolve_by_uuid_or_code(
        Indicator,
        _parse_uuid(row.get("indicator_uuid"), "indicator_uuid", row_number),
        row.get("indicator_code"),
        "code",
        row_number,
        "Indicator",
    )
    relationship_type = _normalize_choice(
        row.get("relationship_type"),
        CONTROLLED_VOCABS["relationship_type"],
        "relationship_type",
        row_number,
        default="",
    )
    defaults = {
        "relationship_type": relationship_type,
        "role": _clean(row.get("role")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        ProgrammeIndicatorLink,
        {"programme": programme, "indicator": indicator},
        defaults,
        mode,
        row_number,
        "ProgrammeIndicatorLink",
    )
    return created, updated


def _import_methodology_dataset_link(row, mode, row_number):
    methodology = _resolve_by_uuid_or_code(
        Methodology,
        _parse_uuid(row.get("methodology_uuid"), "methodology_uuid", row_number),
        row.get("methodology_code"),
        "methodology_code",
        row_number,
        "Methodology",
    )
    dataset = _resolve_by_uuid_or_code(
        DatasetCatalog,
        _parse_uuid(row.get("dataset_uuid"), "dataset_uuid", row_number),
        row.get("dataset_code"),
        "dataset_code",
        row_number,
        "DatasetCatalog",
    )
    relationship_type = _normalize_choice(
        row.get("relationship_type"),
        CONTROLLED_VOCABS["relationship_type"],
        "relationship_type",
        row_number,
        default="",
    )
    defaults = {
        "relationship_type": relationship_type,
        "role": _clean(row.get("role")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        MethodologyDatasetLink,
        {"methodology": methodology, "dataset": dataset},
        defaults,
        mode,
        row_number,
        "MethodologyDatasetLink",
    )
    return created, updated


def _import_methodology_indicator_link(row, mode, row_number):
    methodology = _resolve_by_uuid_or_code(
        Methodology,
        _parse_uuid(row.get("methodology_uuid"), "methodology_uuid", row_number),
        row.get("methodology_code"),
        "methodology_code",
        row_number,
        "Methodology",
    )
    indicator = _resolve_by_uuid_or_code(
        Indicator,
        _parse_uuid(row.get("indicator_uuid"), "indicator_uuid", row_number),
        row.get("indicator_code"),
        "code",
        row_number,
        "Indicator",
    )
    relationship_type = _normalize_choice(
        row.get("relationship_type"),
        CONTROLLED_VOCABS["relationship_type"],
        "relationship_type",
        row_number,
        default="",
    )
    defaults = {
        "relationship_type": relationship_type,
        "role": _clean(row.get("role")),
        "notes": _clean(row.get("notes")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    created_total = 0
    updated_total = 0

    _, created, updated = _upsert_model(
        MethodologyIndicatorLink,
        {"methodology": methodology, "indicator": indicator},
        defaults,
        mode,
        row_number,
        "MethodologyIndicatorLink",
    )
    created_total += created
    updated_total += updated

    version_uuid = _parse_uuid(row.get("methodology_version_uuid"), "methodology_version_uuid", row_number)
    version_label = _clean(row.get("methodology_version"))
    version = None
    if version_uuid:
        version = MethodologyVersion.objects.filter(uuid=version_uuid).first()
        if not version:
            raise CommandError(f"Row {row_number}: MethodologyVersion not found for uuid '{version_uuid}'.")
        if version.methodology_id != methodology.id:
            raise CommandError(
                f"Row {row_number}: MethodologyVersion does not belong to methodology '{methodology.methodology_code}'."
            )
    elif version_label:
        version = MethodologyVersion.objects.filter(methodology=methodology, version=version_label).first()
        if not version:
            raise CommandError(
                f"Row {row_number}: MethodologyVersion '{version_label}' not found for methodology '{methodology.methodology_code}'."
            )
    else:
        active_versions = MethodologyVersion.objects.filter(methodology=methodology, is_active=True)
        if not active_versions.exists():
            raise CommandError(
                f"Row {row_number}: No active MethodologyVersion for methodology '{methodology.methodology_code}'."
            )
        if active_versions.count() > 1:
            raise CommandError(
                f"Row {row_number}: Multiple active MethodologyVersions for methodology '{methodology.methodology_code}'."
            )
        version = active_versions.first()

    source_ref = _clean(row.get("source_ref"))
    source_url = source_ref if source_ref.startswith("http") else ""
    version_defaults = {
        "is_primary": False,
        "notes": _clean(row.get("notes")),
        "source": source_url,
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
    }
    _, created, updated = _upsert_model(
        IndicatorMethodologyVersionLink,
        {"indicator": indicator, "methodology_version": version},
        version_defaults,
        mode,
        row_number,
        "IndicatorMethodologyVersionLink",
    )
    created_total += created
    updated_total += updated
    return created_total, updated_total



def _import_gbf_goal(row, mode, row_number):
    framework_code = _clean(row.get("framework_code"))
    goal_code = _clean(row.get("goal_code"))
    title = _clean(row.get("goal_title"))
    if not framework_code or not goal_code or not title:
        raise CommandError("framework_code, goal_code, and goal_title are required.")
    framework = _resolve_by_code(Framework, "code", framework_code, row_number, "Framework")
    defaults = {
        "title": title,
        "official_text": _clean(row.get("official_text")),
        "description": _clean(row.get("description")),
        "is_active": _parse_bool(row.get("is_active"), "is_active", row_number, default=True),
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        FrameworkGoal,
        {"framework": framework, "code": goal_code},
        defaults,
        mode,
        row_number,
        "FrameworkGoal",
    )
    return created, updated


def _import_gbf_target(row, mode, row_number):
    framework_code = _clean(row.get("framework_code"))
    target_code = _clean(row.get("target_code"))
    title = _clean(row.get("target_title"))
    if not framework_code or not target_code or not title:
        raise CommandError("framework_code, target_code, and target_title are required.")
    framework = _resolve_by_code(Framework, "code", framework_code, row_number, "Framework")
    goal_code = _clean(row.get("goal_code"))
    goal = None
    if goal_code:
        goal = FrameworkGoal.objects.filter(framework=framework, code=goal_code).first()
        if not goal:
            raise CommandError(f"Row {row_number}: FrameworkGoal not found for code '{goal_code}'.")
    is_active = _parse_bool(row.get("is_active"), "is_active", row_number, default=True)
    defaults = {
        "title": title,
        "official_text": _clean(row.get("official_text")),
        "description": _clean(row.get("description")),
        "goal": goal,
        "status": LifecycleStatus.PUBLISHED if is_active else LifecycleStatus.ARCHIVED,
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        FrameworkTarget,
        {"framework": framework, "code": target_code},
        defaults,
        mode,
        row_number,
        "FrameworkTarget",
    )
    return created, updated


def _import_gbf_indicator(row, mode, row_number):
    framework_code = _clean(row.get("framework_code"))
    indicator_code = _clean(row.get("indicator_code"))
    title = _clean(row.get("indicator_title"))
    if not framework_code or not indicator_code or not title:
        raise CommandError("framework_code, indicator_code, and indicator_title are required.")
    framework = _resolve_by_code(Framework, "code", framework_code, row_number, "Framework")
    target_code = _clean(row.get("framework_target_code"))
    framework_target = None
    if target_code:
        framework_target = FrameworkTarget.objects.filter(framework=framework, code=target_code).first()
        if not framework_target:
            raise CommandError(f"Row {row_number}: FrameworkTarget not found for code '{target_code}'.")
    indicator_type = _normalize_choice(
        row.get("indicator_type"),
        CONTROLLED_VOCABS["framework_indicator_type"],
        "indicator_type",
        row_number,
        default=FrameworkIndicatorType.OTHER,
    )
    is_active = _parse_bool(row.get("is_active"), "is_active", row_number, default=True)
    defaults = {
        "framework_target": framework_target,
        "title": title,
        "indicator_type": indicator_type,
        "description": _clean(row.get("description")),
        "status": LifecycleStatus.PUBLISHED if is_active else LifecycleStatus.ARCHIVED,
        "source_system": _clean(row.get("source_system")),
        "source_ref": _clean(row.get("source_ref")),
    }
    _, created, updated = _upsert_model(
        FrameworkIndicator,
        {"framework": framework, "code": indicator_code},
        defaults,
        mode,
        row_number,
        "FrameworkIndicator",
    )
    return created, updated


_IMPORTERS = {
    "organisation": _import_organisation,
    "sensitivity_class": _import_sensitivity_class,
    "data_agreement": _import_data_agreement,
    "framework": _import_framework,
    "monitoring_programme": _import_monitoring_programme,
    "dataset_catalog": _import_dataset_catalog,
    "methodology": _import_methodology,
    "methodology_version": _import_methodology_version,
    "programme_dataset_link": _import_programme_dataset_link,
    "programme_indicator_link": _import_programme_indicator_link,
    "methodology_dataset_link": _import_methodology_dataset_link,
    "methodology_indicator_link": _import_methodology_indicator_link,
    "gbf_goals": _import_gbf_goal,
    "gbf_targets": _import_gbf_target,
    "gbf_indicators": _import_gbf_indicator,
    "framework_goal": _import_gbf_goal,
    "framework_target": _import_gbf_target,
    "framework_indicator": _import_gbf_indicator,
}
