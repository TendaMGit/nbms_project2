import hashlib
import json
from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from nbms_app.models import (
    ReportSectionRevision,
    ReportSuggestedChange,
    SuggestedChangeStatus,
)
from nbms_app.services.audit import record_audit_event


def canonical_json(value):
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload_hash(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def compute_patch(before, after):
    patch = {}
    before = before or {}
    after = after or {}
    keys = sorted(set(before.keys()) | set(after.keys()))
    for key in keys:
        if before.get(key) != after.get(key):
            patch[key] = deepcopy(after.get(key))
    return patch


def apply_patch(content, patch):
    content = deepcopy(content or {})
    for key, value in (patch or {}).items():
        content[key] = deepcopy(value)
    return content


@transaction.atomic
def append_revision(*, section_response, content, author=None, note=""):
    if section_response.locked_for_editing:
        raise ValidationError("Section is locked for editing.")
    content = content or {}
    parent_hash = section_response.current_content_hash or ""
    next_version = int(section_response.current_version or 0) + 1
    content_digest = payload_hash(content)

    existing = ReportSectionRevision.objects.filter(
        section_response=section_response,
        content_hash=content_digest,
    ).first()
    if existing:
        return existing

    revision = ReportSectionRevision.objects.create(
        section_response=section_response,
        version=next_version,
        author=author if getattr(author, "is_authenticated", False) else None,
        content_snapshot=content,
        content_hash=content_digest,
        parent_hash=parent_hash,
        note=note or "",
    )
    section_response.response_json = content
    section_response.current_version = next_version
    section_response.current_content_hash = content_digest
    section_response.updated_by = author if getattr(author, "is_authenticated", False) else None
    section_response.save(
        update_fields=[
            "response_json",
            "current_version",
            "current_content_hash",
            "updated_by",
            "updated_at",
        ]
    )
    return revision


def ensure_initial_revision(*, section_response, author=None):
    if section_response.revisions.exists():
        return
    content = section_response.response_json or {}
    first_hash = payload_hash(content)
    ReportSectionRevision.objects.create(
        section_response=section_response,
        version=1,
        author=author if getattr(author, "is_authenticated", False) else section_response.updated_by,
        content_snapshot=content,
        content_hash=first_hash,
        parent_hash="",
        note="initial",
    )
    section_response.current_version = 1
    section_response.current_content_hash = first_hash
    section_response.save(update_fields=["current_version", "current_content_hash", "updated_at"])


@transaction.atomic
def create_suggested_change(*, section_response, user, base_version, patch_json, rationale=""):
    if section_response.locked_for_editing:
        raise ValidationError("Section is locked for editing.")
    if int(base_version or 0) != int(section_response.current_version or 0):
        raise ValidationError("Section version changed. Refresh before submitting a suggestion.")
    if not isinstance(patch_json, dict) or not patch_json:
        raise ValidationError("patch_json must be a non-empty object.")
    suggestion = ReportSuggestedChange.objects.create(
        section_response=section_response,
        base_version=section_response.current_version,
        patch_json=patch_json,
        diff_patch=patch_json,
        old_value_hash=payload_hash(section_response.response_json or {}),
        proposed_value=apply_patch(section_response.response_json or {}, patch_json or {}),
        rationale=rationale or "",
        created_by=user if getattr(user, "is_authenticated", False) else None,
        status=SuggestedChangeStatus.PROPOSED,
    )
    record_audit_event(
        user,
        "report_suggestion_create",
        section_response,
        metadata={
            "section_response_uuid": str(section_response.uuid),
            "suggested_change_uuid": str(suggestion.uuid),
            "base_version": section_response.current_version,
        },
    )
    return suggestion


@transaction.atomic
def decide_suggested_change(*, suggestion, user, accept, note=""):
    if suggestion.status not in {SuggestedChangeStatus.PROPOSED, SuggestedChangeStatus.PENDING}:
        raise ValidationError("Suggestion is not pending.")

    section_response = suggestion.section_response
    if section_response and section_response.locked_for_editing:
        raise ValidationError("Section is locked for editing.")

    decision_status = SuggestedChangeStatus.ACCEPTED if accept else SuggestedChangeStatus.REJECTED
    suggestion.status = decision_status
    suggestion.decided_by = user if getattr(user, "is_authenticated", False) else None
    suggestion.decided_at = timezone.now()
    suggestion.decision_note = note or ""
    suggestion.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])

    applied_revision = None
    if accept and section_response:
        current_content = section_response.response_json or {}
        merged = apply_patch(current_content, suggestion.diff_patch or suggestion.patch_json or {})
        applied_revision = append_revision(
            section_response=section_response,
            content=merged,
            author=user,
            note=f"accepted_suggestion:{suggestion.uuid}",
        )

    record_audit_event(
        user,
        "report_suggestion_decide",
        section_response or suggestion,
        metadata={
            "section_response_uuid": str(section_response.uuid) if section_response else None,
            "suggested_change_uuid": str(suggestion.uuid),
            "status": decision_status,
            "applied_revision_uuid": str(applied_revision.uuid) if applied_revision else None,
        },
    )
    return suggestion, applied_revision
