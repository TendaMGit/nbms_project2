from django.core.management.base import BaseCommand

from nbms_app.models import ReportSectionTemplate


TEMPLATES = [
    {
        "code": "section-i",
        "title": "Section I: Status of biodiversity",
        "ordering": 1,
        "schema_json": {
            "required": True,
            "fields": [
                {"key": "summary", "label": "Summary of status", "required": True},
                {"key": "key_trends", "label": "Key trends", "required": False},
                {"key": "challenges", "label": "Challenges", "required": False},
            ],
        },
    },
    {
        "code": "section-ii",
        "title": "Section II: Implementation measures",
        "ordering": 2,
        "schema_json": {
            "required": True,
            "fields": [
                {"key": "policy_measures", "label": "Policy measures", "required": True},
                {"key": "financing", "label": "Financing", "required": False},
                {"key": "capacity_building", "label": "Capacity building", "required": False},
            ],
        },
    },
    {
        "code": "section-iii",
        "title": "Section III: National targets progress",
        "ordering": 3,
        "schema_json": {
            "required": True,
            "fields": [
                {"key": "progress_overview", "label": "Progress overview", "required": True},
                {"key": "indicator_highlights", "label": "Indicator highlights", "required": False},
            ],
        },
    },
    {
        "code": "section-iv",
        "title": "Section IV: Support needed",
        "ordering": 4,
        "schema_json": {
            "required": True,
            "fields": [
                {"key": "support_needs", "label": "Support needs", "required": True},
                {"key": "support_received", "label": "Support received", "required": False},
            ],
        },
    },
    {
        "code": "section-v",
        "title": "Section V: Additional information",
        "ordering": 5,
        "schema_json": {
            "required": True,
            "fields": [
                {"key": "annex_notes", "label": "Annex notes", "required": False},
                {"key": "references", "label": "References", "required": False},
            ],
        },
    },
    {
        "code": "section-other-information",
        "title": "Section Other Information (Annex)",
        "ordering": 6,
        "schema_json": {
            "required": False,
            "fields": [
                {
                    "key": "additional_information",
                    "label": "Additional information",
                    "required": False,
                },
                {
                    "key": "additional_documents",
                    "label": "Additional documents",
                    "required": False,
                },
            ],
        },
    },
]


class Command(BaseCommand):
    help = "Seed report section templates for 7NR narrative capture."

    def handle(self, *args, **options):
        created = 0
        for data in TEMPLATES:
            _, was_created = ReportSectionTemplate.objects.update_or_create(
                code=data["code"],
                defaults={
                    "title": data["title"],
                    "ordering": data["ordering"],
                    "schema_json": data["schema_json"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Ensured {len(TEMPLATES)} report section templates ({created} created)."
            )
        )
