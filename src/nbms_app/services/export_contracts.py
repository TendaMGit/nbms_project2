from django.core.exceptions import ValidationError


ORT_NR7_V2_REQUIRED_KEYS = {
    "schema",
    "exporter_version",
    "generated_at",
    "reporting_instance",
    "sections",
    "section_iii_progress",
    "section_iv_goal_progress",
    "section_iv_progress",
    "indicator_data_series",
    "binary_indicator_data",
    "binary_indicator_group_responses",
    "nbms_meta",
}


def _require_dict(value, path):
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object.")
    return value


def _require_list(value, path):
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be an array.")
    return value


def _require_keys(data, required_keys, path):
    missing = [key for key in required_keys if key not in data]
    if missing:
        raise ValidationError(f"{path} is missing required keys: {', '.join(sorted(missing))}.")


def _validate_progress_entries(entries, key_name, path):
    for index, entry in enumerate(entries):
        entry_path = f"{path}[{index}]"
        entry = _require_dict(entry, entry_path)
        _require_keys(entry, {"uuid", key_name, "references"}, entry_path)
        _require_keys(entry, {"progress_status", "progress_level"}, entry_path)
        if not (entry.get("progress_summary") or entry.get("summary")):
            raise ValidationError(f"{entry_path} must include progress_summary (or summary).")
        _require_dict(entry[key_name], f"{entry_path}.{key_name}")
        refs = _require_dict(entry["references"], f"{entry_path}.references")
        _require_keys(
            refs,
            {
                "indicator_data_series_uuids",
                "binary_indicator_response_uuids",
                "evidence_uuids",
                "dataset_release_uuids",
            },
            f"{entry_path}.references",
        )
        for ref_key in (
            "indicator_data_series_uuids",
            "binary_indicator_response_uuids",
            "evidence_uuids",
            "dataset_release_uuids",
        ):
            _require_list(refs[ref_key], f"{entry_path}.references.{ref_key}")


def _validate_indicator_series(series_items, path):
    for index, series in enumerate(series_items):
        series_path = f"{path}[{index}]"
        series = _require_dict(series, series_path)
        _require_keys(series, {"uuid", "identity", "value_type", "points"}, series_path)
        _require_dict(series["identity"], f"{series_path}.identity")
        points = _require_list(series["points"], f"{series_path}.points")
        for point_index, point in enumerate(points):
            point_path = f"{series_path}.points[{point_index}]"
            point = _require_dict(point, point_path)
            _require_keys(point, {"uuid", "year", "disaggregation"}, point_path)
            _require_dict(point["disaggregation"], f"{point_path}.disaggregation")


def _validate_section_structured_content(sections):
    section_map = {item.get("code"): item for item in sections}

    section_i = _require_dict(section_map.get("section-i") or {}, "section[section-i]")
    section_i_content = _require_dict(section_i.get("content") or {}, "section[section-i].content")
    _require_keys(
        section_i_content,
        {
            "reporting_party_name",
            "submission_language",
            "additional_languages",
            "responsible_authorities",
            "contact_name",
            "contact_email",
            "preparation_process",
            "preparation_challenges",
            "acknowledgements",
        },
        "section[section-i].content",
    )
    _require_list(section_i_content.get("additional_languages"), "section[section-i].content.additional_languages")

    section_ii = _require_dict(section_map.get("section-ii") or {}, "section[section-ii]")
    section_ii_content = _require_dict(section_ii.get("content") or {}, "section[section-ii].content")
    _require_keys(
        section_ii_content,
        {
            "nbsap_updated_status",
            "nbsap_updated_other_text",
            "nbsap_expected_completion_date",
            "stakeholders_involved",
            "stakeholder_groups",
            "stakeholder_groups_other_text",
            "stakeholder_groups_notes",
            "nbsap_adopted_status",
            "nbsap_adopted_other_text",
            "nbsap_adoption_mechanism",
            "nbsap_expected_adoption_date",
            "monitoring_system_description",
        },
        "section[section-ii].content",
    )
    _require_list(section_ii_content.get("stakeholder_groups"), "section[section-ii].content.stakeholder_groups")

    section_v = _require_dict(section_map.get("section-v") or {}, "section[section-v]")
    section_v_content = _require_dict(section_v.get("content") or {}, "section[section-v].content")
    _require_keys(
        section_v_content,
        {
            "overall_assessment",
            "decision_15_8_information",
            "decision_15_7_information",
            "decision_15_11_information",
            "plant_conservation_information",
            "additional_notes",
            "evidence_uuids",
        },
        "section[section-v].content",
    )
    _require_list(section_v_content.get("evidence_uuids"), "section[section-v].content.evidence_uuids")


def _validate_binary_items(binary_items, path):
    for index, item in enumerate(binary_items):
        item_path = f"{path}[{index}]"
        item = _require_dict(item, item_path)
        _require_keys(item, {"uuid", "reporting_instance_uuid", "question", "response"}, item_path)
        _require_dict(item["question"], f"{item_path}.question")


def _validate_section_iv_goal_entries(entries, path):
    for index, entry in enumerate(entries):
        entry_path = f"{path}[{index}]"
        entry = _require_dict(entry, entry_path)
        _require_keys(entry, {"uuid", "framework_goal", "progress_summary", "evidence_uuids"}, entry_path)
        _require_dict(entry["framework_goal"], f"{entry_path}.framework_goal")
        _require_list(entry["evidence_uuids"], f"{entry_path}.evidence_uuids")


def _validate_binary_group_responses(entries, path):
    for index, entry in enumerate(entries):
        entry_path = f"{path}[{index}]"
        entry = _require_dict(entry, entry_path)
        _require_keys(entry, {"uuid", "group", "comments"}, entry_path)
        _require_dict(entry["group"], f"{entry_path}.group")


def validate_ort_nr7_v2_payload_shape(payload):
    payload = _require_dict(payload, "payload")
    _require_keys(payload, ORT_NR7_V2_REQUIRED_KEYS, "payload")

    reporting_instance = _require_dict(payload["reporting_instance"], "payload.reporting_instance")
    _require_keys(
        reporting_instance,
        {"uuid", "title", "status", "version_label", "cycle"},
        "payload.reporting_instance",
    )
    cycle = _require_dict(reporting_instance["cycle"], "payload.reporting_instance.cycle")
    _require_keys(cycle, {"uuid", "code", "title", "start_date", "end_date", "due_date"}, "payload.reporting_instance.cycle")

    sections = _require_list(payload["sections"], "payload.sections")
    for index, section in enumerate(sections):
        section_path = f"payload.sections[{index}]"
        section = _require_dict(section, section_path)
        _require_keys(section, {"code", "title", "content"}, section_path)
        _require_dict(section["content"], f"{section_path}.content")
    _validate_section_structured_content(sections)

    _validate_progress_entries(
        _require_list(payload["section_iii_progress"], "payload.section_iii_progress"),
        key_name="national_target",
        path="payload.section_iii_progress",
    )
    _validate_progress_entries(
        _require_list(payload["section_iv_progress"], "payload.section_iv_progress"),
        key_name="framework_target",
        path="payload.section_iv_progress",
    )
    _validate_section_iv_goal_entries(
        _require_list(payload["section_iv_goal_progress"], "payload.section_iv_goal_progress"),
        path="payload.section_iv_goal_progress",
    )
    _validate_indicator_series(
        _require_list(payload["indicator_data_series"], "payload.indicator_data_series"),
        path="payload.indicator_data_series",
    )
    _validate_binary_items(
        _require_list(payload["binary_indicator_data"], "payload.binary_indicator_data"),
        path="payload.binary_indicator_data",
    )
    _validate_binary_group_responses(
        _require_list(payload["binary_indicator_group_responses"], "payload.binary_indicator_group_responses"),
        path="payload.binary_indicator_group_responses",
    )

    meta = _require_dict(payload["nbms_meta"], "payload.nbms_meta")
    _require_keys(meta, {"instance_uuid", "ruleset_code", "generated_at", "conformance_flags"}, "payload.nbms_meta")
    _require_dict(meta["conformance_flags"], "payload.nbms_meta.conformance_flags")
    return payload


def validate_ort_indicator_tabular_rows(rows):
    rows = _require_list(rows, "rows")
    for index, row in enumerate(rows):
        row_path = f"rows[{index}]"
        row = _require_dict(row, row_path)
        _require_keys(row, {"indicator_code", "year"}, row_path)
        if not row.get("indicator_code"):
            raise ValidationError(f"{row_path}.indicator_code must not be empty.")

        has_numeric = row.get("value_numeric") not in (None, "")
        has_text = row.get("value_text") not in (None, "")
        if not (has_numeric or has_text):
            raise ValidationError(f"{row_path} must include value_numeric or value_text.")

        try:
            int(row["year"])
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{row_path}.year must be an integer.") from exc

        disaggregation = row.get("disaggregation", {})
        if disaggregation in (None, ""):
            disaggregation = {}
        _require_dict(disaggregation, f"{row_path}.disaggregation")
    return rows
