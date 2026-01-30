import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nbms_app.models import (
    DataAgreement,
    DatasetCatalog,
    Framework,
    FrameworkGoal,
    FrameworkIndicator,
    FrameworkTarget,
    Indicator,
    IndicatorMethodologyVersionLink,
    LifecycleStatus,
    Methodology,
    MethodologyDatasetLink,
    MethodologyVersion,
    MonitoringProgramme,
    Organisation,
    ProgrammeDatasetLink,
    ProgrammeIndicatorLink,
    SensitivityClass,
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
        "methodology_version",
        "methodology_version_uuid",
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

EXAMPLE_ROWS = {
    "organisation": {
        "org_code": "ORG-1",
        "org_name": "Org One",
        "org_type": "Government",
        "is_active": "true",
    },
    "sensitivity_class": {
        "sensitivity_code": "PUB",
        "sensitivity_name": "Public",
        "access_level_default": "public",
        "consent_required_default": "false",
        "is_active": "true",
    },
    "data_agreement": {
        "agreement_code": "AGR-1",
        "title": "Agreement 1",
        "agreement_type": "MOU",
        "parties_org_codes": "ORG-1",
        "is_active": "true",
    },
    "framework": {
        "framework_code": "GBF",
        "title": "Global Biodiversity Framework",
        "description": "Framework overview.",
        "status": "published",
        "sensitivity": "public",
    },
    "monitoring_programme": {
        "programme_code": "PROG-1",
        "title": "Monitoring Programme 1",
        "programme_type": "national",
        "lead_org_code": "ORG-1",
        "sensitivity_code": "PUB",
        "update_frequency": "annual",
        "is_active": "true",
    },
    "dataset_catalog": {
        "dataset_code": "DS-1",
        "title": "Dataset 1",
        "custodian_org_code": "ORG-1",
        "access_level": "public",
        "sensitivity_code": "PUB",
        "update_frequency": "annual",
        "is_active": "true",
    },
    "methodology": {
        "methodology_code": "METH-1",
        "title": "Methodology 1",
        "owner_org_code": "ORG-1",
        "is_active": "true",
    },
    "methodology_version": {
        "methodology_code": "METH-1",
        "version": "1.0",
        "status": "draft",
        "parameters_json": "{}",
        "is_active": "true",
    },
    "programme_dataset_link": {
        "programme_code": "PROG-1",
        "dataset_code": "DS-1",
        "relationship_type": "lead",
        "is_active": "true",
    },
    "programme_indicator_link": {
        "programme_code": "PROG-1",
        "indicator_code": "IND-1",
        "relationship_type": "lead",
        "is_active": "true",
    },
    "methodology_dataset_link": {
        "methodology_code": "METH-1",
        "dataset_code": "DS-1",
        "relationship_type": "supporting",
        "is_active": "true",
    },
    "methodology_indicator_link": {
        "methodology_code": "METH-1",
        "methodology_version": "1.0",
        "indicator_code": "IND-1",
        "relationship_type": "supporting",
        "is_active": "true",
    },
    "gbf_goals": {
        "framework_code": "GBF",
        "goal_code": "A",
        "goal_title": "Reduce threats to biodiversity",
        "is_active": "true",
    },
    "gbf_targets": {
        "framework_code": "GBF",
        "target_code": "T1",
        "goal_code": "A",
        "target_title": "Target 1",
        "is_active": "true",
    },
    "gbf_indicators": {
        "framework_code": "GBF",
        "framework_target_code": "T1",
        "indicator_code": "IND-1",
        "indicator_title": "Indicator 1",
        "indicator_type": "other",
        "is_active": "true",
    },
}

EXAMPLE_ROWS["framework_goal"] = EXAMPLE_ROWS["gbf_goals"]
EXAMPLE_ROWS["framework_target"] = EXAMPLE_ROWS["gbf_targets"]
EXAMPLE_ROWS["framework_indicator"] = EXAMPLE_ROWS["gbf_indicators"]


def _build_example_row(entity):
    row = {name: "" for name in ENTITY_HEADERS[entity]}
    row.update(EXAMPLE_ROWS.get(entity, {}))
    return row


class Command(BaseCommand):
    help = "Export reference catalog entities to CSV templates."

    def add_arguments(self, parser):
        parser.add_argument("--entity", required=True, choices=sorted(ENTITY_HEADERS.keys()))
        parser.add_argument("--out", required=True, help="Output CSV path.")
        parser.add_argument(
            "--template",
            action="store_true",
            help="Write a CSV template with headers and an example row.",
        )

    def handle(self, *args, **options):
        entity = options["entity"]
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        exporter = _EXPORTERS.get(entity)
        if not exporter:
            raise CommandError(f"Unsupported entity: {entity}")

        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=ENTITY_HEADERS[entity])
            writer.writeheader()
            if options["template"]:
                example = EXAMPLE_ROWS.get(entity)
                if example is None:
                    raise CommandError(f"No template example available for entity: {entity}")
                writer.writerow(_build_example_row(entity))
            else:
                exporter(writer)

        label = "template" if options["template"] else "export"
        self.stdout.write(self.style.SUCCESS(f"Wrote {entity} {label} to {out_path}"))



def _format_date(value):
    return value.isoformat() if value else ""


def _join_codes(items):
    codes = []
    for item in items:
        if hasattr(item, "org_code") and item.org_code:
            codes.append(item.org_code)
        elif hasattr(item, "dataset_code") and item.dataset_code:
            codes.append(item.dataset_code)
        else:
            codes.append(str(item.uuid))
    return ";".join(codes)


def _export_organisation(writer):
    for org in Organisation.objects.order_by("org_code", "name"):
        writer.writerow(
            {
                "org_uuid": str(org.uuid),
                "org_code": org.org_code or "",
                "org_name": org.name,
                "org_type": org.org_type or "",
                "parent_org_code": org.parent_org.org_code if org.parent_org else "",
                "website_url": org.website_url or "",
                "primary_contact_name": org.primary_contact_name or "",
                "primary_contact_email": org.primary_contact_email or "",
                "alternative_contact_name": org.alternative_contact_name or "",
                "alternative_contact_email": org.alternative_contact_email or "",
                "notes": org.notes or "",
                "is_active": str(org.is_active),
                "source_system": org.source_system or "",
                "source_ref": org.source_ref or "",
            }
        )


def _export_sensitivity_class(writer):
    for sensitivity in SensitivityClass.objects.order_by("sensitivity_code"):
        writer.writerow(
            {
                "sensitivity_code": sensitivity.sensitivity_code,
                "sensitivity_name": sensitivity.sensitivity_name,
                "description": sensitivity.description or "",
                "access_level_default": sensitivity.access_level_default,
                "consent_required_default": str(sensitivity.consent_required_default),
                "redaction_policy": sensitivity.redaction_policy or "",
                "legal_basis": sensitivity.legal_basis or "",
                "notes": sensitivity.notes or "",
                "is_active": str(sensitivity.is_active),
                "source_system": sensitivity.source_system or "",
                "source_ref": sensitivity.source_ref or "",
            }
        )


def _export_data_agreement(writer):
    for agreement in DataAgreement.objects.order_by("agreement_code"):
        writer.writerow(
            {
                "agreement_uuid": str(agreement.uuid),
                "agreement_code": agreement.agreement_code or "",
                "title": agreement.title,
                "agreement_type": agreement.agreement_type or "",
                "parties_org_codes": _join_codes(agreement.parties.all()),
                "start_date": _format_date(agreement.start_date),
                "end_date": _format_date(agreement.end_date),
                "status": agreement.status or "",
                "licence": agreement.licence or "",
                "restrictions_summary": agreement.restrictions_summary or "",
                "benefit_sharing_terms": agreement.benefit_sharing_terms or "",
                "citation_requirement": agreement.citation_requirement or "",
                "document_url": agreement.document_url or "",
                "primary_contact_name": agreement.primary_contact_name or "",
                "primary_contact_email": agreement.primary_contact_email or "",
                "is_active": str(agreement.is_active),
                "source_system": agreement.source_system or "",
                "source_ref": agreement.source_ref or "",
            }
        )


def _export_framework(writer):
    for framework in Framework.objects.order_by("code"):
        writer.writerow(
            {
                "framework_uuid": str(framework.uuid),
                "framework_code": framework.code,
                "title": framework.title,
                "description": framework.description or "",
                "organisation_code": framework.organisation.org_code if framework.organisation else "",
                "status": framework.status,
                "sensitivity": framework.sensitivity,
                "review_note": framework.review_note or "",
            }
        )


def _export_monitoring_programme(writer):
    programmes = MonitoringProgramme.objects.prefetch_related("partners").order_by("programme_code")
    for programme in programmes:
        writer.writerow(
            {
                "programme_uuid": str(programme.uuid),
                "programme_code": programme.programme_code or "",
                "title": programme.title,
                "description": programme.description or "",
                "programme_type": programme.programme_type or "",
                "lead_org_code": programme.lead_org.org_code if programme.lead_org else "",
                "partner_org_codes": _join_codes(programme.partners.all()),
                "start_year": programme.start_year or "",
                "end_year": programme.end_year or "",
                "geographic_scope": programme.geographic_scope or "",
                "spatial_coverage_description": programme.spatial_coverage_description or "",
                "taxonomic_scope": programme.taxonomic_scope or "",
                "ecosystem_scope": programme.ecosystem_scope or "",
                "objectives": programme.objectives or "",
                "sampling_design_summary": programme.sampling_design_summary or "",
                "update_frequency": programme.update_frequency or "",
                "qa_process_summary": programme.qa_process_summary or "",
                "sensitivity_code": programme.sensitivity_class.sensitivity_code if programme.sensitivity_class else "",
                "consent_required": str(programme.consent_required),
                "agreement_code": programme.agreement.agreement_code if programme.agreement else "",
                "website_url": programme.website_url or "",
                "primary_contact_name": programme.primary_contact_name or "",
                "primary_contact_email": programme.primary_contact_email or "",
                "alternative_contact_name": programme.alternative_contact_name or "",
                "alternative_contact_email": programme.alternative_contact_email or "",
                "is_active": str(programme.is_active),
                "source_system": programme.source_system or "",
                "source_ref": programme.source_ref or "",
                "notes": programme.notes or "",
            }
        )


def _export_dataset_catalog(writer):
    datasets = DatasetCatalog.objects.order_by("dataset_code")
    for dataset in datasets:
        writer.writerow(
            {
                "dataset_uuid": str(dataset.uuid),
                "dataset_code": dataset.dataset_code or "",
                "title": dataset.title,
                "description": dataset.description or "",
                "dataset_type": dataset.dataset_type or "",
                "custodian_org_code": dataset.custodian_org.org_code if dataset.custodian_org else "",
                "producer_org_code": dataset.producer_org.org_code if dataset.producer_org else "",
                "licence": dataset.licence or "",
                "access_level": dataset.access_level or "",
                "sensitivity_code": dataset.sensitivity_class.sensitivity_code if dataset.sensitivity_class else "",
                "consent_required": str(dataset.consent_required),
                "agreement_code": dataset.agreement.agreement_code if dataset.agreement else "",
                "temporal_start": _format_date(dataset.temporal_start),
                "temporal_end": _format_date(dataset.temporal_end),
                "update_frequency": dataset.update_frequency or "",
                "spatial_coverage_description": dataset.spatial_coverage_description or "",
                "spatial_resolution": dataset.spatial_resolution or "",
                "taxonomy_standard": dataset.taxonomy_standard or "",
                "ecosystem_classification": dataset.ecosystem_classification or "",
                "doi_or_identifier": dataset.doi_or_identifier or "",
                "landing_page_url": dataset.landing_page_url or "",
                "api_endpoint_url": dataset.api_endpoint_url or "",
                "file_formats": dataset.file_formats or "",
                "qa_status": dataset.qa_status or "",
                "citation": dataset.citation or "",
                "keywords": dataset.keywords or "",
                "last_updated_date": _format_date(dataset.last_updated_date),
                "is_active": str(dataset.is_active),
                "source_system": dataset.source_system or "",
                "source_ref": dataset.source_ref or "",
            }
        )



def _export_methodology(writer):
    for methodology in Methodology.objects.order_by("methodology_code"):
        writer.writerow(
            {
                "methodology_uuid": str(methodology.uuid),
                "methodology_code": methodology.methodology_code or "",
                "title": methodology.title,
                "description": methodology.description or "",
                "owner_org_code": methodology.owner_org.org_code if methodology.owner_org else "",
                "scope": methodology.scope or "",
                "references_url": methodology.references_url or "",
                "is_active": str(methodology.is_active),
                "source_system": methodology.source_system or "",
                "source_ref": methodology.source_ref or "",
            }
        )


def _export_methodology_version(writer):
    versions = MethodologyVersion.objects.select_related("methodology").order_by("methodology__methodology_code", "version")
    for version in versions:
        writer.writerow(
            {
                "methodology_version_uuid": str(version.uuid),
                "methodology_code": version.methodology.methodology_code,
                "version": version.version,
                "status": version.status,
                "effective_date": _format_date(version.effective_date),
                "deprecated_date": _format_date(version.deprecated_date),
                "change_log": version.change_log or "",
                "protocol_url": version.protocol_url or "",
                "computational_script_url": version.computational_script_url or "",
                "parameters_json": json.dumps(version.parameters_json or {}, sort_keys=True),
                "qa_steps_summary": version.qa_steps_summary or "",
                "peer_reviewed": str(version.peer_reviewed),
                "approval_body": version.approval_body or "",
                "approval_reference": version.approval_reference or "",
                "is_active": str(version.is_active),
                "source_system": version.source_system or "",
                "source_ref": version.source_ref or "",
            }
        )


def _export_programme_dataset_link(writer):
    links = ProgrammeDatasetLink.objects.select_related("programme", "dataset").order_by("programme__programme_code")
    for link in links:
        writer.writerow(
            {
                "programme_code": link.programme.programme_code or "",
                "programme_uuid": str(link.programme.uuid),
                "dataset_code": link.dataset.dataset_code or "",
                "dataset_uuid": str(link.dataset.uuid),
                "relationship_type": link.relationship_type or "",
                "role": link.role or "",
                "notes": link.notes or "",
                "is_active": str(link.is_active),
                "source_system": link.source_system or "",
                "source_ref": link.source_ref or "",
            }
        )


def _export_programme_indicator_link(writer):
    links = ProgrammeIndicatorLink.objects.select_related("programme", "indicator").order_by("programme__programme_code")
    for link in links:
        writer.writerow(
            {
                "programme_code": link.programme.programme_code or "",
                "programme_uuid": str(link.programme.uuid),
                "indicator_code": link.indicator.code,
                "indicator_uuid": str(link.indicator.uuid),
                "relationship_type": link.relationship_type or "",
                "role": link.role or "",
                "notes": link.notes or "",
                "is_active": str(link.is_active),
                "source_system": link.source_system or "",
                "source_ref": link.source_ref or "",
            }
        )


def _export_methodology_dataset_link(writer):
    links = MethodologyDatasetLink.objects.select_related("methodology", "dataset").order_by("methodology__methodology_code")
    for link in links:
        writer.writerow(
            {
                "methodology_code": link.methodology.methodology_code or "",
                "methodology_uuid": str(link.methodology.uuid),
                "dataset_code": link.dataset.dataset_code or "",
                "dataset_uuid": str(link.dataset.uuid),
                "relationship_type": link.relationship_type or "",
                "role": link.role or "",
                "notes": link.notes or "",
                "is_active": str(link.is_active),
                "source_system": link.source_system or "",
                "source_ref": link.source_ref or "",
            }
        )


def _export_methodology_indicator_link(writer):
    links = (
        IndicatorMethodologyVersionLink.objects.select_related(
            "methodology_version",
            "methodology_version__methodology",
            "indicator",
        )
        .order_by("methodology_version__methodology__methodology_code", "methodology_version__version")
    )
    for link in links:
        methodology = link.methodology_version.methodology
        writer.writerow(
            {
                "methodology_code": methodology.methodology_code or "",
                "methodology_uuid": str(methodology.uuid),
                "methodology_version": link.methodology_version.version or "",
                "methodology_version_uuid": str(link.methodology_version.uuid),
                "indicator_code": link.indicator.code,
                "indicator_uuid": str(link.indicator.uuid),
                "relationship_type": "",
                "role": "",
                "notes": link.notes or "",
                "is_active": str(link.is_active),
                "source_system": "",
                "source_ref": link.source or "",
            }
        )


def _export_gbf_goals(writer):
    goals = FrameworkGoal.objects.select_related("framework").order_by("framework__code", "sort_order", "code")
    for goal in goals:
        writer.writerow(
            {
                "framework_code": goal.framework.code,
                "goal_code": goal.code,
                "goal_title": goal.title,
                "official_text": goal.official_text or "",
                "description": goal.description or "",
                "is_active": str(goal.is_active),
                "source_system": goal.source_system or "",
                "source_ref": goal.source_ref or "",
            }
        )


def _export_gbf_targets(writer):
    targets = FrameworkTarget.objects.select_related("framework", "goal").order_by("framework__code", "code")
    for target in targets:
        writer.writerow(
            {
                "framework_code": target.framework.code,
                "target_code": target.code,
                "goal_code": target.goal.code if target.goal else "",
                "target_title": target.title,
                "official_text": target.official_text or "",
                "description": target.description or "",
                "is_active": str(target.status == LifecycleStatus.PUBLISHED),
                "source_system": target.source_system or "",
                "source_ref": target.source_ref or "",
            }
        )


def _export_gbf_indicators(writer):
    indicators = FrameworkIndicator.objects.select_related("framework", "framework_target").order_by("framework__code", "code")
    for indicator in indicators:
        writer.writerow(
            {
                "framework_code": indicator.framework.code,
                "framework_target_code": indicator.framework_target.code if indicator.framework_target else "",
                "indicator_code": indicator.code,
                "indicator_title": indicator.title,
                "indicator_type": indicator.indicator_type,
                "description": indicator.description or "",
                "is_active": str(indicator.status == LifecycleStatus.PUBLISHED),
                "source_system": indicator.source_system or "",
                "source_ref": indicator.source_ref or "",
            }
        )


_EXPORTERS = {
    "organisation": _export_organisation,
    "sensitivity_class": _export_sensitivity_class,
    "data_agreement": _export_data_agreement,
    "framework": _export_framework,
    "monitoring_programme": _export_monitoring_programme,
    "dataset_catalog": _export_dataset_catalog,
    "methodology": _export_methodology,
    "methodology_version": _export_methodology_version,
    "programme_dataset_link": _export_programme_dataset_link,
    "programme_indicator_link": _export_programme_indicator_link,
    "methodology_dataset_link": _export_methodology_dataset_link,
    "methodology_indicator_link": _export_methodology_indicator_link,
    "gbf_goals": _export_gbf_goals,
    "gbf_targets": _export_gbf_targets,
    "gbf_indicators": _export_gbf_indicators,
    "framework_goal": _export_gbf_goals,
    "framework_target": _export_gbf_targets,
    "framework_indicator": _export_gbf_indicators,
}
