from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from nbms_app.models import (
    Framework,
    FrameworkTarget,
    GovernedNarrative,
    GovernedNarrativeEntityType,
    GovernedNarrativeVersion,
    Indicator,
    LifecycleStatus,
    QaStatus,
    SensitivityLevel,
)
from nbms_app.services.audit import record_audit_event
from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_SECRETARIAT,
    ROLE_SECTION_LEAD,
    can_edit_object,
    filter_queryset_for_user,
    is_system_admin,
    user_has_role,
)


_INLINE_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_INLINE_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


@dataclass(frozen=True)
class NarrativeEntityContext:
    entity_type: str
    entity_key: str
    entity_label: str
    sensitivity: str
    obj: object | None = None


def narrative_block_defaults(entity_type: str) -> list[dict[str, str]]:
    summary_title = "Executive summary" if entity_type == GovernedNarrativeEntityType.DASHBOARD else "Interpretation"
    return [
        {"id": "interpretation", "title": summary_title, "body": ""},
        {"id": "key_messages", "title": "Key messages", "body": ""},
        {"id": "data_limitations", "title": "Data limitations", "body": ""},
        {"id": "what_changed", "title": "What changed", "body": ""},
    ]


def resolve_narrative_entity(entity_type: str, entity_id: str, user) -> NarrativeEntityContext:
    normalized_type = (entity_type or "").strip().lower()
    normalized_id = (entity_id or "").strip()
    if normalized_type not in set(GovernedNarrativeEntityType.values):
        raise ValidationError("Unsupported narrative entity type.")
    if not normalized_id:
        raise ValidationError("Narrative entity identifier is required.")

    if normalized_type == GovernedNarrativeEntityType.DASHBOARD:
        if not getattr(user, "is_authenticated", False):
            raise PermissionDenied("Dashboard narratives require authentication.")
        return NarrativeEntityContext(
            entity_type=normalized_type,
            entity_key=normalized_id,
            entity_label="NBMS Home Dashboard",
            sensitivity=SensitivityLevel.INTERNAL,
            obj=None,
        )

    if normalized_type == GovernedNarrativeEntityType.FRAMEWORK:
        obj = filter_queryset_for_user(
            Framework.objects.select_related("organisation", "created_by"),
            user,
            perm="nbms_app.view_framework",
        ).filter(code__iexact=normalized_id).first()
        if not obj:
            raise ValidationError("Framework narrative entity was not found.")
        return NarrativeEntityContext(
            entity_type=normalized_type,
            entity_key=obj.code,
            entity_label=obj.title or obj.code,
            sensitivity=obj.sensitivity,
            obj=obj,
        )

    if normalized_type == GovernedNarrativeEntityType.TARGET:
        if ":" not in normalized_id:
            raise ValidationError("Target narrative identifiers must use FRAMEWORK:TARGET format.")
        framework_code, target_code = [part.strip() for part in normalized_id.split(":", 1)]
        obj = filter_queryset_for_user(
            FrameworkTarget.objects.select_related("framework", "organisation", "created_by"),
            user,
            perm="nbms_app.view_frameworktarget",
        ).filter(framework__code__iexact=framework_code, code__iexact=target_code).first()
        if not obj:
            raise ValidationError("Target narrative entity was not found.")
        return NarrativeEntityContext(
            entity_type=normalized_type,
            entity_key=f"{obj.framework.code}:{obj.code}",
            entity_label=f"{obj.framework.code} {obj.code} - {obj.title}",
            sensitivity=obj.sensitivity,
            obj=obj,
        )

    obj = filter_queryset_for_user(
        Indicator.objects.select_related("organisation", "created_by"),
        user,
        perm="nbms_app.view_indicator",
    ).filter(uuid=normalized_id).first()
    if not obj:
        raise ValidationError("Indicator narrative entity was not found.")
    return NarrativeEntityContext(
        entity_type=normalized_type,
        entity_key=str(obj.uuid),
        entity_label=f"{obj.code} - {obj.title}",
        sensitivity=obj.sensitivity,
        obj=obj,
    )


def can_edit_narrative_entity(user, context: NarrativeEntityContext) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_system_admin(user):
        return True
    if context.entity_type == GovernedNarrativeEntityType.DASHBOARD:
        return bool(user_has_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN))
    if context.obj is not None and can_edit_object(user, context.obj):
        return True
    return bool(user_has_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN, ROLE_INDICATOR_LEAD))


def get_or_create_narrative(context: NarrativeEntityContext, user=None) -> GovernedNarrative:
    narrative, created = GovernedNarrative.objects.get_or_create(
        entity_type=context.entity_type,
        entity_key=context.entity_key,
        defaults={
            "entity_label": context.entity_label,
            "title": f"{context.entity_label} narrative",
            "sections_json": narrative_block_defaults(context.entity_type),
            "markdown_snapshot": sections_to_markdown(narrative_block_defaults(context.entity_type)),
            "html_snapshot": render_sections_html(narrative_block_defaults(context.entity_type)),
            "summary_text": "",
            "sensitivity": context.sensitivity or SensitivityLevel.INTERNAL,
            "created_by": user if getattr(user, "is_authenticated", False) else None,
            "updated_by": user if getattr(user, "is_authenticated", False) else None,
        },
    )
    dirty_fields: list[str] = []
    if narrative.entity_label != context.entity_label:
        narrative.entity_label = context.entity_label
        dirty_fields.append("entity_label")
    if context.sensitivity and narrative.sensitivity != context.sensitivity:
        narrative.sensitivity = context.sensitivity
        dirty_fields.append("sensitivity")
    if dirty_fields:
        dirty_fields.append("updated_at")
        narrative.save(update_fields=dirty_fields)
    if created:
        create_narrative_version(narrative=narrative, user=user, note="initial")
    return narrative


def create_narrative_version(*, narrative: GovernedNarrative, user=None, note: str = "") -> GovernedNarrativeVersion:
    next_version = int(narrative.current_version or 0) + 1
    version = GovernedNarrativeVersion.objects.create(
        narrative=narrative,
        version=next_version,
        sections_json=narrative.sections_json or [],
        markdown_snapshot=narrative.markdown_snapshot or "",
        html_snapshot=narrative.html_snapshot or "",
        summary_text=narrative.summary_text or "",
        status=narrative.status,
        qa_status=narrative.qa_status,
        provenance_url=narrative.provenance_url or "",
        note=note,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    narrative.current_version = next_version
    narrative.save(update_fields=["current_version", "updated_at"])
    return version


def save_narrative_draft(narrative: GovernedNarrative, payload: dict, user) -> GovernedNarrative:
    sections = normalize_sections(payload.get("sections"), narrative.entity_type)
    narrative.entity_label = str(payload.get("entity_label") or narrative.entity_label or "").strip() or narrative.entity_label
    narrative.title = str(payload.get("title") or narrative.title or "Narrative").strip() or "Narrative"
    narrative.sections_json = sections
    narrative.markdown_snapshot = sections_to_markdown(sections)
    narrative.html_snapshot = render_sections_html(sections)
    narrative.summary_text = build_summary_text(sections)
    narrative.status = LifecycleStatus.DRAFT
    narrative.provenance_url = str(payload.get("provenance_url") or narrative.provenance_url or "").strip()
    narrative.updated_by = user
    narrative.save(
        update_fields=[
            "entity_label",
            "title",
            "sections_json",
            "markdown_snapshot",
            "html_snapshot",
            "summary_text",
            "status",
            "provenance_url",
            "updated_by",
            "updated_at",
        ]
    )
    create_narrative_version(narrative=narrative, user=user, note="draft")
    record_audit_event(
        user,
        "narrative_draft_save",
        narrative,
        metadata={
            "entity_type": narrative.entity_type,
            "entity_key": narrative.entity_key,
            "version": narrative.current_version,
        },
    )
    return narrative


def submit_narrative(narrative: GovernedNarrative, payload: dict, user) -> GovernedNarrative:
    sections = normalize_sections(payload.get("sections"), narrative.entity_type)
    narrative.title = str(payload.get("title") or narrative.title or "Narrative").strip() or "Narrative"
    narrative.sections_json = sections
    narrative.markdown_snapshot = sections_to_markdown(sections)
    narrative.html_snapshot = render_sections_html(sections)
    narrative.summary_text = build_summary_text(sections)
    narrative.status = LifecycleStatus.PENDING_REVIEW
    narrative.qa_status = QaStatus.DRAFT
    narrative.provenance_url = str(payload.get("provenance_url") or narrative.provenance_url or "").strip()
    narrative.submitted_at = timezone.now()
    narrative.updated_by = user
    narrative.save(
        update_fields=[
            "title",
            "sections_json",
            "markdown_snapshot",
            "html_snapshot",
            "summary_text",
            "status",
            "qa_status",
            "provenance_url",
            "submitted_at",
            "updated_by",
            "updated_at",
        ]
    )
    create_narrative_version(narrative=narrative, user=user, note="submit")
    record_audit_event(
        user,
        "narrative_submit",
        narrative,
        metadata={
            "entity_type": narrative.entity_type,
            "entity_key": narrative.entity_key,
            "version": narrative.current_version,
            "status": narrative.status,
        },
    )
    return narrative


def serialize_narrative(narrative: GovernedNarrative, *, can_edit: bool) -> dict:
    sections = normalize_sections(narrative.sections_json, narrative.entity_type)
    return {
        "uuid": str(narrative.uuid),
        "entity_type": narrative.entity_type,
        "entity_key": narrative.entity_key,
        "entity_label": narrative.entity_label,
        "title": narrative.title,
        "status": narrative.status,
        "qa_status": narrative.qa_status,
        "sensitivity": narrative.sensitivity,
        "provenance_url": narrative.provenance_url,
        "current_version": narrative.current_version,
        "submitted_at": narrative.submitted_at.isoformat() if narrative.submitted_at else None,
        "updated_at": narrative.updated_at.isoformat() if narrative.updated_at else None,
        "updated_by": narrative.updated_by.username if narrative.updated_by_id else None,
        "summary_text": narrative.summary_text,
        "sections": [
            {
                "id": section["id"],
                "title": section["title"],
                "body": section["body"],
                "html": render_markdown(section["body"]),
            }
            for section in sections
        ],
        "available_block_types": narrative_block_defaults(narrative.entity_type),
        "can_edit": can_edit,
    }


def serialize_narrative_versions(narrative: GovernedNarrative) -> list[dict]:
    return [
        {
            "uuid": str(version.uuid),
            "version": version.version,
            "status": version.status,
            "qa_status": version.qa_status,
            "provenance_url": version.provenance_url,
            "summary_text": version.summary_text,
            "markdown_snapshot": version.markdown_snapshot,
            "html_snapshot": version.html_snapshot,
            "sections": normalize_sections(version.sections_json, narrative.entity_type),
            "note": version.note,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "created_by": version.created_by.username if version.created_by_id else None,
        }
        for version in narrative.versions.all()
    ]


def normalize_sections(raw_sections, entity_type: str) -> list[dict[str, str]]:
    defaults = narrative_block_defaults(entity_type)
    default_lookup = {row["id"]: row for row in defaults}
    if not isinstance(raw_sections, list) or not raw_sections:
        return defaults

    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_sections):
        if not isinstance(item, dict):
            continue
        section_id = str(item.get("id") or "").strip() or defaults[min(index, len(defaults) - 1)]["id"]
        if section_id in seen_ids:
            continue
        seen_ids.add(section_id)
        fallback = default_lookup.get(section_id, {"title": section_id.replace("_", " ").title()})
        rows.append(
            {
                "id": section_id,
                "title": str(item.get("title") or fallback["title"]).strip() or fallback["title"],
                "body": str(item.get("body") or "").strip(),
            }
        )

    for default_row in defaults:
        if default_row["id"] not in seen_ids:
            rows.append(default_row.copy())
    return rows


def sections_to_markdown(sections: list[dict[str, str]]) -> str:
    blocks = []
    for section in sections:
        title = str(section.get("title") or "").strip()
        body = str(section.get("body") or "").strip()
        if title:
            blocks.append(f"## {title}\n\n{body}".strip())
        elif body:
            blocks.append(body)
    return "\n\n".join(blocks).strip()


def build_summary_text(sections: list[dict[str, str]]) -> str:
    for section in sections:
        body = str(section.get("body") or "").strip()
        if body:
            return body[:400]
    return ""


def render_sections_html(sections: list[dict[str, str]]) -> str:
    parts = []
    for section in sections:
        title = escape(str(section.get("title") or "").strip())
        body = str(section.get("body") or "").strip()
        section_html = []
        if title:
            section_html.append(f"<h3>{title}</h3>")
        section_html.append(render_markdown(body))
        parts.append(f"<section>{''.join(section_html)}</section>")
    return "".join(parts)


def render_markdown(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    blocks: list[str] = []
    buffer: list[str] = []
    in_list = False

    def flush_paragraph():
        nonlocal buffer
        if buffer:
            blocks.append(f"<p>{render_inline(' '.join(buffer).strip())}</p>")
            buffer = []

    def close_list():
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            close_list()
            continue
        if line.startswith("### "):
            flush_paragraph()
            close_list()
            blocks.append(f"<h3>{render_inline(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            flush_paragraph()
            close_list()
            blocks.append(f"<h2>{render_inline(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            flush_paragraph()
            close_list()
            blocks.append(f"<h1>{render_inline(line[2:])}</h1>")
            continue
        if line.startswith("- ") or line.startswith("* "):
            flush_paragraph()
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{render_inline(line[2:])}</li>")
            continue
        close_list()
        buffer.append(line)

    flush_paragraph()
    close_list()
    return "".join(blocks)


def render_inline(text: str) -> str:
    escaped = escape(str(text or ""))
    escaped = _INLINE_BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _INLINE_ITALIC_RE.sub(r"<em>\1</em>", escaped)
    return escaped
