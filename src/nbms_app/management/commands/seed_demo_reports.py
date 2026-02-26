from datetime import date

from django.core.management.base import BaseCommand

from nbms_app.models import Organisation, ReportTemplatePackResponse, ReportingCycle, ReportingInstance, User
from nbms_app.services.reporting_collab import append_revision, ensure_initial_revision
from nbms_app.services.reporting_workflow import resolve_cbd_pack
from nbms_app.services.template_packs import build_default_response_payload


DEMO_SECTION_CONTENT = {
    "section-i": {
        "country_or_reporting_party_name": "South Africa",
        "report_label": "NR7",
        "submission_language": "English",
        "additional_languages": ["French"],
        "responsible_authorities": "SANBI and DFFE are jointly responsible for authoring and sign-off.",
        "focal_point_name": "NBMS Secretariat",
        "focal_point_title": "National Focal Point",
        "focal_point_organisation": "SANBI",
        "focal_point_email": "nbms@example.org",
        "focal_point_phone": "+27-12-000-0000",
        "report_preparation_process": "Whole-of-government authoring workflow.",
        "report_preparation_challenges": "Dataset harmonization and reporting cadence alignment.",
        "acknowledgements": "Contributions from SANBI, DFFE, and provincial partners.",
        "preparers_list": [
            {"name": "Author 1", "organisation": "SANBI", "role": "Lead author"},
            {"name": "Author 2", "organisation": "DFFE", "role": "Contributor"},
        ],
        "reviewers_list": [
            {"name": "Reviewer 1", "organisation": "Technical Committee", "role": "Technical reviewer"},
        ],
        "public_availability": "internal",
    },
    "section-ii": {
        "nbsap_title": "South Africa National Biodiversity Strategy and Action Plan",
        "nbsap_adoption_date": "2020-01-01",
        "nbsap_revision_date": "2025-06-30",
        "nbsap_update_status": "in_progress",
        "nbsap_preparation_process": "National consultative process coordinated by SANBI and DFFE.",
        "stakeholder_groups": ["indigenous_and_local_communities", "women", "youth", "private_sector"],
        "stakeholder_involvement_narrative": "IPLC and youth consultations informed priority actions.",
        "alignment_to_gbf_and_national_targets": "NBSAP actions were aligned to GBF goals and national targets.",
        "national_monitoring_system_description": "NBMS programme-driven architecture with indicator and spatial pipelines.",
        "linkages_indicator_codes": ["GBF-H-A1-ZA"],
        "linkages_dataset_codes": ["NBMS-DS-001"],
        "linkages_evidence_uuids": [],
        "relevant_policy_context": "Aligned to national biodiversity and climate policy frameworks.",
        "optional_attachment_evidence_uuids": [],
    },
    "section-iii": {
        "target_progress_rows": [
            {
                "national_target_code": "ZA-NT-01",
                "national_target_title": "Target 1",
                "actions_taken": "Ecosystem planning updated.",
                "progress_level": "on_track",
                "progress_summary": "Spatial plans integrated.",
                "outcomes_and_impacts": "Expanded planning coverage in priority landscapes.",
                "challenges_and_approaches": "Scale local implementation and improve finance flows.",
                "indicator_links": ["NBMS-GBF-PA-COVERAGE"],
                "dataset_links": ["NBMS-DS-001"],
                "evidence_links": [],
                "sdg_and_other_mea_linkages": "SDG 15 alignment and cross-MEA reporting benefits.",
                "spatial_outputs_used": ["protected-area-priority-zones"],
            },
            {
                "national_target_code": "ZA-NT-02",
                "national_target_title": "Target 6",
                "actions_taken": "IAS containment priorities implemented.",
                "progress_level": "insufficient_rate",
                "progress_summary": "Pressure reduced in priority basins.",
                "outcomes_and_impacts": "Improved IAS surveillance in selected catchments.",
                "challenges_and_approaches": "Increase local authority compliance and investment.",
                "indicator_links": ["NBMS-GBF-IAS-PRESSURE"],
                "dataset_links": [],
                "evidence_links": [],
                "sdg_and_other_mea_linkages": "SDG 15 and IAS decision reporting.",
                "spatial_outputs_used": [],
            },
        ],
        "section_narrative": "Section III consolidates target-by-target progress evidence.",
    },
    "section-iv": {
        "goal_progress_rows": [
            {
                "framework_goal_code": "A",
                "framework_goal_title": "Goal A",
                "summary_national_progress": "Progress is positive but uneven across provinces.",
                "key_achievements": "Protected area gains and restoration momentum.",
                "key_gaps": "Financing and local implementation consistency.",
            }
        ],
        "target_progress_rows": [
            {
                "framework_target_code": "T1",
                "framework_target_title": "Target 1",
                "progress_level": "some_progress",
                "narrative": "National planning and implementation actions are underway.",
                "key_measures": "Planning reforms and implementation support.",
                "barriers": "Capacity and financing barriers remain.",
                "indicator_links": ["GBF-H-A1-ZA"],
                "dataset_links": ["NBMS-DS-001"],
                "evidence_links": [],
            }
        ],
        "binary_indicator_rows": [
            {
                "framework_indicator_code": "GBF-B-01",
                "binary_response": "yes",
                "justification": "Required legal and institutional provisions are active.",
            }
        ],
        "section_narrative": "Section IV links national progress with GBF goals and targets.",
    },
    "section-v": {
        "overall_implementation_effectiveness": "Implementation is progressing with measurable outcomes.",
        "key_achievements": "Protected area coverage increased and governance strengthened.",
        "gaps_and_challenges": "Financing and local capacity remain key barriers.",
        "capacity_needs": "Local authority capacity and data stewardship support are required.",
        "capacity_need_tags": ["capacity_building", "local_government", "data_stewardship"],
        "financial_needs": "Blended financing for implementation scale-up.",
        "financial_needs_table": [
            {"year": 2022, "source": "National budget", "amount_zar_millions": 125.0}
        ],
        "technology_needs": "Data interoperability and API modernization.",
        "data_and_knowledge_needs": "Expanded disaggregation and improved evidence traceability.",
        "stakeholder_engagement_and_iplc": "Sensitivity-aware IPLC engagement structures are in place.",
        "lessons_learned": "Early multi-author review reduces late-cycle revisions.",
        "planned_next_steps": "Finalize review cycle and prepare submission package.",
    },
    "annex": {
        "annex_items": [
            {
                "decision_topic_code": "COP16-31",
                "title": "Binary indicator updates",
                "summary": "All required binary indicators seeded and partially populated.",
            }
        ]
    },
}


class Command(BaseCommand):
    help = "Seed demo NR7/NR8 reporting instances with CBD national report workspace content."

    def handle(self, *args, **options):
        pack = resolve_cbd_pack()
        org, _ = Organisation.objects.get_or_create(
            org_code="SANBI",
            defaults={"name": "South African National Biodiversity Institute"},
        )
        publisher_org, _ = Organisation.objects.get_or_create(
            org_code="DFFE",
            defaults={"name": "Department of Forestry, Fisheries and the Environment"},
        )
        user = User.objects.filter(username="Tenda").first() or User.objects.filter(is_superuser=True).order_by("id").first()

        created_instances = []
        for cycle_code, title, start_year in (
            ("NR7", "Seventh National Report", 2024),
            ("NR8", "Eighth National Report", 2027),
        ):
            cycle, _ = ReportingCycle.objects.update_or_create(
                code=cycle_code,
                defaults={
                    "title": title,
                    "start_date": date(start_year, 1, 1),
                    "end_date": date(start_year + 2, 12, 31),
                    "due_date": date(start_year + 3, 3, 31),
                    "submission_window_start": date(start_year + 2, 10, 1),
                    "submission_window_end": date(start_year + 3, 3, 31),
                    "default_language": "English",
                    "allowed_languages": ["English"],
                    "is_active": cycle_code == "NR8",
                },
            )
            instance, _ = ReportingInstance.objects.update_or_create(
                cycle=cycle,
                version_label="v1",
                defaults={
                    "report_title": f"South Africa {cycle_code}",
                    "country_name": "South Africa",
                    "focal_point_org": org,
                    "publishing_authority_org": publisher_org,
                    "is_public": False,
                    "created_by": user,
                    "updated_by": user,
                },
            )
            created_instances.append(instance)

            for section in pack.sections.filter(is_active=True).order_by("ordering", "code"):
                response, _created = ReportTemplatePackResponse.objects.get_or_create(
                    reporting_instance=instance,
                    section=section,
                    defaults={"response_json": build_default_response_payload(section), "updated_by": user},
                )
                ensure_initial_revision(section_response=response, author=user)
                content = DEMO_SECTION_CONTENT.get(section.code)
                if content:
                    append_revision(
                        section_response=response,
                        content=content,
                        author=user,
                        note=f"seed_demo_reports:{cycle_code}",
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo report instances for NR7/NR8 ({len(created_instances)} instances)."
            )
        )
