# Sections I-V UI Notes

This document describes the structured UI routes for Sections I-V and key behaviors.

## Routes
- Section hub: `/reporting/instances/<uuid>/sections/`
- Section I (report context): `/reporting/instances/<uuid>/section-i/`
- Section II (NBSAP status): `/reporting/instances/<uuid>/section-ii/`
- Section III (national targets progress): `/reporting/instances/<uuid>/section-iii/`
- Section IV goals: `/reporting/instances/<uuid>/section-iv/goals/`
- Section IV targets: `/reporting/instances/<uuid>/section-iv/`
- Section IV binary indicators: `/reporting/instances/<uuid>/section-iv/binary-indicators/`
- Section V (conclusions): `/reporting/instances/<uuid>/section-v/`

## Access control
- All pages require staff or system admin access.
- Instance-scoped ABAC is enforced via `_require_section_progress_access`.
- Non-admins are blocked from edits when a reporting instance is frozen.

## Freeze behavior
- If a reporting instance is frozen, pages render read-only and POST returns 403 for non-admins.

## Binary indicator UX
- Group comments are captured via `BinaryIndicatorGroupResponse`.
- Question responses support single, multiple, and text answers.
- Header questions (parent questions with children) render as display-only.
- Ordering is deterministic: groups by `(target_code, ordering, key)`, questions by `(sort_order, section, number, question_key)`.

## Section II conditional fields
- Q1 completion date shows for update status `no` or `in_progress`.
- Stakeholder detail fields show only when stakeholder involvement is `yes`.
- Adoption mechanism shows for `yes` or `in_progress`.
- Adoption expected date and specify text show for `no`, `other`, or `in_progress`.
