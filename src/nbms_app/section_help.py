"""
Centralized help text for ORT NR7 Section I-V structured capture.

This module is used by Django forms and can be reused by API/Angular surfaces.
"""

SECTION_FIELD_HELP = {
    "section_i": {
        "reporting_party_name": "Country name as it should appear in the official NR7 submission.",
        "submission_language": "Primary language used for this report submission.",
        "additional_languages": "Optional additional languages available for submission materials.",
        "responsible_authorities": "Lead authorities responsible for preparing and validating this report.",
        "contact_name": "Primary contact person for follow-up questions on this report.",
        "contact_email": "Official email address for ORT follow-up communication.",
        "preparation_process": "Summarize coordination steps, consultations, and drafting process.",
        "preparation_challenges": "Describe constraints affecting evidence quality, timing, or completeness.",
        "acknowledgements": "Contributors, institutions, and partners acknowledged for this report.",
    },
    "section_ii": {
        "nbsap_updated_status": "Current publication status of the updated NBSAP.",
        "nbsap_updated_other_text": "Required when status is 'Other'. Provide exact status wording.",
        "nbsap_expected_completion_date": "Required when update status is 'No' or 'In progress'.",
        "stakeholders_involved": "Whether stakeholder groups participated in NBSAP update.",
        "stakeholder_groups": "Select all participating stakeholder groups.",
        "stakeholder_groups_other_text": "Required when 'Other' is selected in stakeholder groups.",
        "stakeholder_groups_notes": "Optional notes about stakeholder engagement quality and depth.",
        "nbsap_adopted_status": "Formal adoption status of NBSAP by the competent authority.",
        "nbsap_adopted_other_text": "Required when adoption status is 'No' or 'Other'.",
        "nbsap_adoption_mechanism": "Required when status is 'Yes' or 'In progress'.",
        "nbsap_expected_adoption_date": "Required for 'No', 'Other', and 'In progress' adoption status.",
        "monitoring_system_description": "Describe the national biodiversity monitoring system used for NR7 evidence.",
    },
    "section_iii": {
        "progress_status": "Workflow status used for internal tracking.",
        "progress_level": "ORT progress level for this national target.",
        "summary": "Required narrative summary of progress toward this national target.",
        "actions_taken": "Main actions taken that contributed to progress.",
        "outcomes": "Observed outcomes from actions taken.",
        "challenges_and_approaches": "Key challenges and approaches used to address them.",
        "effectiveness_examples": "Examples or cases demonstrating effectiveness.",
        "sdg_and_other_agreements": "How progress relates to SDGs and other MEA commitments.",
        "support_needed": "Support needs for accelerated implementation.",
        "period_start": "Start date of reporting period for this progress statement.",
        "period_end": "End date of reporting period for this progress statement.",
    },
    "section_iv_goal": {
        "progress_summary": "Required summary of national contribution to this GBF 2050 goal.",
        "actions_taken": "Main actions contributing to the goal.",
        "outcomes": "Observed outcomes relevant to the goal.",
        "challenges_and_approaches": "Key implementation challenges and responses.",
        "sdg_and_other_agreements": "How this goal contribution links with SDGs and other agreements.",
        "evidence_items": "Optional evidence files or links supporting this goal narrative.",
    },
    "section_iv_target": {
        "progress_status": "Workflow status used for internal tracking.",
        "progress_level": "ORT progress level for this framework target.",
        "summary": "Required narrative summary of progress toward this framework target.",
        "actions_taken": "Main actions taken for this framework target.",
        "outcomes": "Observed outcomes from actions.",
        "challenges_and_approaches": "Key challenges and approaches used to address them.",
        "effectiveness_examples": "Examples or cases demonstrating effectiveness.",
        "sdg_and_other_agreements": "How progress links with SDGs and other agreements.",
        "support_needed": "Support needs for accelerated implementation.",
        "period_start": "Start date of reporting period for this progress statement.",
        "period_end": "End date of reporting period for this progress statement.",
    },
    "section_v": {
        "overall_assessment": "Required overall assessment for Section V conclusions.",
        "decision_15_8_information": "Optional additional information requested under Decision 15/8.",
        "decision_15_7_information": "Optional additional information requested under Decision 15/7.",
        "decision_15_11_information": "Optional additional information requested under Decision 15/11.",
        "plant_conservation_information": "Optional plant-conservation-specific additional information.",
        "additional_notes": "Additional notes not captured in the structured fields above.",
        "evidence_items": "Optional evidence supporting conclusions.",
    },
}


SECTION_FIELD_WHY = {
    "section_i": "Section I establishes accountability, language, and national point-of-contact details used across the report.",
    "section_ii": "Section II provides implementation context for interpreting progress against national targets.",
    "section_iii": "Section III is the core national-target progress evidence block for ORT submissions.",
    "section_iv_goal": "Section IV goal narratives explain contributions to GBF 2050 outcomes.",
    "section_iv_target": "Section IV target progress links national action to GBF target-level outcomes.",
    "section_v": "Section V captures strategic conclusions and decisions that frame implementation priorities.",
}


def build_section_help_payload():
    payload = {}
    for section_key, fields in SECTION_FIELD_HELP.items():
        payload[section_key] = {
            "why_it_matters": SECTION_FIELD_WHY.get(section_key, ""),
            "fields": {field: {"help": text, "why_it_matters": SECTION_FIELD_WHY.get(section_key, "")} for field, text in fields.items()},
        }
    return payload


def apply_section_help(form, section_key):
    section_help = SECTION_FIELD_HELP.get(section_key, {})
    for field_name, help_text in section_help.items():
        if field_name in form.fields:
            form.fields[field_name].help_text = help_text
