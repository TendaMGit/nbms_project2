import csv

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from nbms_app.models import Framework, Organisation


pytestmark = pytest.mark.django_db


ORG_HEADERS = [
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
]

DATASET_HEADERS = [
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
]

FRAMEWORK_HEADERS = [
    "framework_uuid",
    "framework_code",
    "title",
    "description",
    "organisation_code",
    "status",
    "sensitivity",
    "review_note",
]


def _write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _row(headers, **values):
    row = {header: "" for header in headers}
    row.update(values)
    return row


def test_reference_catalog_import_upsert_updates(tmp_path):
    path = tmp_path / "orgs.csv"
    _write_csv(
        path,
        ORG_HEADERS,
        [
            _row(
                ORG_HEADERS,
                org_code="ORG-1",
                org_name="Org One",
                org_type="Government",
                is_active="true",
            )
        ],
    )
    call_command("reference_catalog_import", entity="organisation", file=str(path))
    org = Organisation.objects.get(org_code="ORG-1")
    assert org.name == "Org One"

    _write_csv(
        path,
        ORG_HEADERS,
        [
            _row(
                ORG_HEADERS,
                org_code="ORG-1",
                org_name="Org One Updated",
                org_type="Government",
                is_active="true",
            )
        ],
    )
    call_command("reference_catalog_import", entity="organisation", file=str(path))
    org.refresh_from_db()
    assert org.name == "Org One Updated"


def test_reference_catalog_import_invalid_vocab_rejected(tmp_path):
    Organisation.objects.create(name="Org A", org_code="ORG-A")
    path = tmp_path / "datasets.csv"
    _write_csv(
        path,
        DATASET_HEADERS,
        [
            _row(
                DATASET_HEADERS,
                dataset_code="DS-1",
                title="Dataset 1",
                custodian_org_code="ORG-A",
                access_level="invalid",
                is_active="true",
            )
        ],
    )
    with pytest.raises(CommandError):
        call_command(
            "reference_catalog_import",
            entity="dataset_catalog",
            file=str(path),
            strict=True,
        )


def test_reference_catalog_import_requires_references(tmp_path):
    path = tmp_path / "datasets_missing.csv"
    _write_csv(
        path,
        DATASET_HEADERS,
        [
            _row(
                DATASET_HEADERS,
                dataset_code="DS-2",
                title="Dataset 2",
                custodian_org_code="MISSING",
                access_level="internal",
                is_active="true",
            )
        ],
    )
    with pytest.raises(CommandError):
        call_command(
            "reference_catalog_import",
            entity="dataset_catalog",
            file=str(path),
            strict=True,
        )


def test_reference_catalog_import_framework_happy_path(tmp_path):
    Organisation.objects.create(name="Org A", org_code="ORG-A")
    path = tmp_path / "framework.csv"
    _write_csv(
        path,
        FRAMEWORK_HEADERS,
        [
            _row(
                FRAMEWORK_HEADERS,
                framework_code="GBF",
                title="Global Biodiversity Framework",
                organisation_code="ORG-A",
                status="published",
                sensitivity="public",
            )
        ],
    )
    call_command("reference_catalog_import", entity="framework", file=str(path))
    framework = Framework.objects.get(code="GBF")
    assert framework.title == "Global Biodiversity Framework"
    assert framework.organisation.org_code == "ORG-A"


def test_reference_catalog_import_reports_row_errors(tmp_path, capsys):
    path = tmp_path / "datasets_missing.csv"
    _write_csv(
        path,
        DATASET_HEADERS,
        [
            _row(
                DATASET_HEADERS,
                dataset_code="DS-2",
                title="Dataset 2",
                custodian_org_code="MISSING",
                access_level="internal",
                is_active="true",
            )
        ],
    )
    call_command(
        "reference_catalog_import",
        entity="dataset_catalog",
        file=str(path),
        strict=False,
    )
    captured = capsys.readouterr()
    assert "Row 2:" in captured.err
    assert "Organisation" in captured.err


def test_reference_catalog_export_template_includes_example(tmp_path):
    path = tmp_path / "framework_template.csv"
    call_command(
        "reference_catalog_export",
        entity="framework",
        out=str(path),
        template=True,
    )
    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][1] == "framework_code"
    assert len(rows) >= 2
