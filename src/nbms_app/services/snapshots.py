import hashlib
import json

from django.core.exceptions import ValidationError

from nbms_app.exports.ort_nr7_v2 import build_ort_nr7_v2_payload
from nbms_app.models import ReportingSnapshot
from nbms_app.services.authorization import is_system_admin
from nbms_app.services.readiness import compute_release_readiness_report


SNAPSHOT_TYPE_NR7_V2 = "NR7_V2_EXPORT"


class _StrictUserProxy:
    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        if name in {"is_staff", "is_superuser"}:
            return False
        return getattr(self._user, name)


def _strict_user(user):
    if not user:
        return user
    if is_system_admin(user):
        return user
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return _StrictUserProxy(user)
    return user


def _canonical_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_payload(payload):
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def create_reporting_snapshot(*, instance, user, note=None):
    export_user = _strict_user(user)
    payload = build_ort_nr7_v2_payload(instance=instance, user=export_user)
    readiness_report, summary = compute_release_readiness_report(instance)
    payload_hash = _hash_payload(payload)

    existing = ReportingSnapshot.objects.filter(
        reporting_instance=instance,
        payload_hash=payload_hash,
    ).first()
    if existing:
        return existing

    return ReportingSnapshot.objects.create(
        reporting_instance=instance,
        snapshot_type=SNAPSHOT_TYPE_NR7_V2,
        payload_json=payload,
        payload_hash=payload_hash,
        exporter_schema=payload.get("schema", ""),
        exporter_version=payload.get("exporter_version", ""),
        readiness_report_json=readiness_report,
        readiness_overall_ready=bool(summary.get("overall_ready")),
        readiness_blocking_gap_count=int(summary.get("blocking_gap_count") or 0),
        created_by=user if getattr(user, "is_authenticated", False) else None,
        notes=note or "",
    )


def _stable_json(value):
    return json.dumps(value or {}, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _diff_sections(a_sections, b_sections):
    a_map = {section.get("code"): section for section in a_sections or []}
    b_map = {section.get("code"): section for section in b_sections or []}

    added = sorted([code for code in b_map if code not in a_map])
    removed = sorted([code for code in a_map if code not in b_map])
    modified = []
    for code in sorted(set(a_map) & set(b_map)):
        if (a_map[code].get("content") or {}) != (b_map[code].get("content") or {}):
            modified.append(code)
    return {"added": added, "removed": removed, "modified": modified}


def _progress_key(entry, kind):
    if kind == "iii":
        target = entry.get("national_target") or {}
        return target.get("code") or ""
    target = entry.get("framework_target") or {}
    return f"{target.get('framework_code', '')}:{target.get('code', '')}"


def _diff_progress_entries(a_entries, b_entries, kind):
    a_map = {(_progress_key(entry, kind)): entry for entry in a_entries or []}
    b_map = {(_progress_key(entry, kind)): entry for entry in b_entries or []}

    added = sorted([key for key in b_map if key not in a_map])
    removed = sorted([key for key in a_map if key not in b_map])
    modified = []
    for key in sorted(set(a_map) & set(b_map)):
        a_entry = a_map[key]
        b_entry = b_map[key]
        fields = [
            "progress_status",
            "summary",
            "actions_taken",
            "outcomes",
            "challenges",
            "support_needed",
            "period_start",
            "period_end",
            "references",
        ]
        changed_fields = [field for field in fields if a_entry.get(field) != b_entry.get(field)]
        if changed_fields:
            modified.append({"key": key, "changed_fields": sorted(changed_fields)})
    return {"added": added, "removed": removed, "modified": modified}


def _series_identity(series):
    identity = series.get("identity") or {}
    if identity.get("framework_indicator_code"):
        return identity.get("framework_indicator_code")
    if identity.get("indicator_code"):
        return identity.get("indicator_code")
    return series.get("uuid") or ""


def _diff_indicator_series(a_series, b_series):
    a_map = {item.get("uuid"): item for item in a_series or []}
    b_map = {item.get("uuid"): item for item in b_series or []}

    added = sorted([_series_identity(b_map[key]) for key in b_map if key not in a_map])
    removed = sorted([_series_identity(a_map[key]) for key in a_map if key not in b_map])
    modified = []
    for key in sorted(set(a_map) & set(b_map)):
        a_item = a_map[key]
        b_item = b_map[key]
        metadata_fields = [
            "identity",
            "title",
            "unit",
            "value_type",
            "methodology",
            "source_notes",
            "disaggregation_schema",
        ]
        changed_fields = [field for field in metadata_fields if a_item.get(field) != b_item.get(field)]

        def point_key(point):
            return (point.get("year"), _stable_json(point.get("disaggregation")))

        def point_map(points):
            return {point_key(point): point for point in points or []}

        a_points = point_map(a_item.get("points"))
        b_points = point_map(b_item.get("points"))
        added_points = sorted([key for key in b_points if key not in a_points])
        removed_points = sorted([key for key in a_points if key not in b_points])
        changed_points = []
        for key_point in sorted(set(a_points) & set(b_points)):
            a_point = a_points[key_point]
            b_point = b_points[key_point]
            fields = [
                "value_numeric",
                "value_text",
                "dataset_release_uuid",
                "source_url",
                "footnote",
            ]
            if any(a_point.get(field) != b_point.get(field) for field in fields):
                changed_points.append({"year": key_point[0], "disaggregation": key_point[1]})

        if changed_fields or added_points or removed_points or changed_points:
            modified.append(
                {
                    "series": _series_identity(a_item),
                    "changed_fields": sorted(changed_fields),
                    "points_added": added_points,
                    "points_removed": removed_points,
                    "points_modified": changed_points,
                }
            )

    return {"added": added, "removed": removed, "modified": modified}


def _binary_key(item):
    question = item.get("question") or {}
    return f"{question.get('framework_indicator_code', '')}:{question.get('group_key', '')}:{question.get('question_key', '')}"


def _diff_binary_responses(a_items, b_items):
    a_map = {(_binary_key(item)): item for item in a_items or []}
    b_map = {(_binary_key(item)): item for item in b_items or []}

    added = sorted([key for key in b_map if key not in a_map])
    removed = sorted([key for key in a_map if key not in b_map])
    modified = []
    for key in sorted(set(a_map) & set(b_map)):
        a_item = a_map[key]
        b_item = b_map[key]
        changed_fields = []
        if a_item.get("response") != b_item.get("response"):
            changed_fields.append("response")
        if a_item.get("comments") != b_item.get("comments"):
            changed_fields.append("comments")
        if changed_fields:
            modified.append({"key": key, "changed_fields": sorted(changed_fields)})
    return {"added": added, "removed": removed, "modified": modified}


def diff_snapshots(a_payload, b_payload):
    if not a_payload or not b_payload:
        raise ValidationError("Both snapshots are required for diffing.")

    sections = _diff_sections(a_payload.get("sections"), b_payload.get("sections"))
    section_iii = _diff_progress_entries(
        a_payload.get("section_iii_progress"),
        b_payload.get("section_iii_progress"),
        "iii",
    )
    section_iv = _diff_progress_entries(
        a_payload.get("section_iv_progress"),
        b_payload.get("section_iv_progress"),
        "iv",
    )
    indicator_series = _diff_indicator_series(
        a_payload.get("indicator_data_series"),
        b_payload.get("indicator_data_series"),
    )
    binary_responses = _diff_binary_responses(
        a_payload.get("binary_indicator_data"),
        b_payload.get("binary_indicator_data"),
    )

    changed_paths = []
    for code in sections["modified"]:
        changed_paths.append(f"sections.{code}")
    for entry in section_iii["modified"]:
        changed_paths.append(f"section_iii_progress.{entry['key']}")
    for entry in section_iv["modified"]:
        changed_paths.append(f"section_iv_progress.{entry['key']}")
    for entry in indicator_series["modified"]:
        changed_paths.append(f"indicator_data_series.{entry['series']}")
    for entry in binary_responses["modified"]:
        changed_paths.append(f"binary_indicator_data.{entry['key']}")

    def strip_known(payload):
        scrubbed = dict(payload)
        scrubbed.pop("generated_at", None)
        scrubbed.pop("sections", None)
        scrubbed.pop("section_iii_progress", None)
        scrubbed.pop("section_iv_progress", None)
        scrubbed.pop("indicator_data_series", None)
        scrubbed.pop("binary_indicator_data", None)
        meta = dict(scrubbed.get("nbms_meta") or {})
        meta.pop("generated_at", None)
        scrubbed["nbms_meta"] = meta
        return scrubbed

    other_changes_detected = strip_known(a_payload) != strip_known(b_payload)

    return {
        "sections": sections,
        "section_iii_progress": section_iii,
        "section_iv_progress": section_iv,
        "indicator_data_series": indicator_series,
        "binary_indicator_data": binary_responses,
        "other_changes_detected": other_changes_detected,
        "changed_paths": sorted(changed_paths)[:50],
    }


def diff_snapshot_readiness(snapshot_a, snapshot_b):
    report_a = snapshot_a.readiness_report_json or {}
    report_b = snapshot_b.readiness_report_json or {}
    summary_a = report_a.get("summary", {}) or {}
    summary_b = report_b.get("summary", {}) or {}

    def blocker_codes(report):
        return {
            item.get("code")
            for item in (report.get("diagnostics", {}) or {}).get("top_blockers", [])
            if item.get("code")
        }

    codes_a = blocker_codes(report_a)
    codes_b = blocker_codes(report_b)

    return {
        "overall_ready": {
            "from": summary_a.get("overall_ready"),
            "to": summary_b.get("overall_ready"),
        },
        "blocking_gap_count": {
            "from": summary_a.get("blocking_gap_count"),
            "to": summary_b.get("blocking_gap_count"),
        },
        "top_blockers_added": sorted(codes_b - codes_a),
        "top_blockers_removed": sorted(codes_a - codes_b),
    }
