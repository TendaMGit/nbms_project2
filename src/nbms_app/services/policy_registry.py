from dataclasses import dataclass


@dataclass(frozen=True)
class RoutePolicy:
    key: str
    description: str
    instance_scoped: bool = False
    instance_kwarg: str = "instance_uuid"
    requires_staff_or_system_admin: bool = True
    no_leakage_expected: bool = True


def _policy(
    *,
    key: str,
    description: str,
    instance_scoped: bool = False,
    requires_staff_or_system_admin: bool = True,
):
    return RoutePolicy(
        key=key,
        description=description,
        instance_scoped=instance_scoped,
        requires_staff_or_system_admin=requires_staff_or_system_admin,
    )


ROUTE_POLICY_REGISTRY = {
    # Management
    "manage_organisation_list": _policy(
        key="management.organisation.list",
        description="List organisations in management workspace.",
    ),
    "manage_organisation_create": _policy(
        key="management.organisation.create",
        description="Create organisation records in management workspace.",
    ),
    "manage_organisation_edit": _policy(
        key="management.organisation.edit",
        description="Edit organisation records in management workspace.",
    ),
    "manage_user_list": _policy(
        key="management.user.list",
        description="List users in management workspace.",
    ),
    "manage_user_create": _policy(
        key="management.user.create",
        description="Create users in management workspace.",
    ),
    "manage_user_edit": _policy(
        key="management.user.edit",
        description="Edit users in management workspace.",
    ),
    "manage_user_send_reset": _policy(
        key="management.user.send_reset",
        description="Send password reset email to managed user.",
    ),
    "review_queue": _policy(
        key="management.review_queue.view",
        description="View pending review queue for targets/indicators.",
    ),
    "review_detail": _policy(
        key="management.review_queue.detail",
        description="View pending review item detail.",
    ),
    "review_action": _policy(
        key="management.review_queue.action",
        description="Approve or reject pending review item.",
    ),
    # Exports
    "export_ort_nr7_narrative_instance": _policy(
        key="reporting.instance.export.ort_nr7_narrative",
        description="Build ORT NR7 narrative payload for scoped reporting instance.",
        instance_scoped=True,
    ),
    "export_ort_nr7_v2_instance": _policy(
        key="reporting.instance.export.ort_nr7_v2",
        description="Build ORT NR7 v2 payload for scoped reporting instance.",
        instance_scoped=True,
    ),
    # Reporting cycles/instances
    "reporting_cycle_list": _policy(
        key="reporting.cycle.list",
        description="List reporting cycles.",
    ),
    "reporting_cycle_create": _policy(
        key="reporting.cycle.create",
        description="Create reporting cycles.",
    ),
    "reporting_cycle_detail": _policy(
        key="reporting.cycle.detail",
        description="View reporting cycle detail.",
    ),
    "reporting_instance_create": _policy(
        key="reporting.instance.create",
        description="Create reporting instances.",
    ),
    "reporting_instance_detail": _policy(
        key="reporting.instance.detail",
        description="View reporting instance detail.",
        instance_scoped=True,
    ),
    "reporting_set_current_instance": _policy(
        key="reporting.instance.current.set",
        description="Set the current reporting instance in session context.",
        instance_scoped=True,
    ),
    "reporting_clear_current_instance": _policy(
        key="reporting.instance.current.clear",
        description="Clear current reporting instance from session context.",
    ),
    "reporting_instance_freeze": _policy(
        key="reporting.instance.freeze",
        description="Freeze or unfreeze reporting instance.",
        instance_scoped=True,
    ),
    # Reporting sections
    "reporting_instance_sections": _policy(
        key="reporting.instance.sections.view",
        description="View reporting section workspace for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_edit": _policy(
        key="reporting.instance.section.edit",
        description="Edit generic report section response for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_preview": _policy(
        key="reporting.instance.section.preview",
        description="Preview generic report section response for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_i": _policy(
        key="reporting.instance.section_i.edit",
        description="View/edit Section I structured capture for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_ii": _policy(
        key="reporting.instance.section_ii.edit",
        description="View/edit Section II structured capture for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iii": _policy(
        key="reporting.instance.section_iii.view",
        description="View Section III target progress list for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iii_edit": _policy(
        key="reporting.instance.section_iii.edit",
        description="Edit Section III target progress for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iv_goals": _policy(
        key="reporting.instance.section_iv_goals.view",
        description="View Section IV goal progress list for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iv_goal_edit": _policy(
        key="reporting.instance.section_iv_goals.edit",
        description="Edit Section IV goal progress for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iv": _policy(
        key="reporting.instance.section_iv.view",
        description="View Section IV framework target progress list for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iv_edit": _policy(
        key="reporting.instance.section_iv.edit",
        description="Edit Section IV framework target progress for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_iv_binary_indicators": _policy(
        key="reporting.instance.section_iv_binary.edit",
        description="Edit Section IV binary indicator responses for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_section_v": _policy(
        key="reporting.instance.section_v.edit",
        description="View/edit Section V structured capture for scoped instance.",
        instance_scoped=True,
    ),
    # Approvals and consent (role-gated but not strictly staff-only)
    "reporting_instance_approvals": _policy(
        key="reporting.instance.approvals.view",
        description="View approval workspace for scoped instance.",
        instance_scoped=True,
        requires_staff_or_system_admin=False,
    ),
    "reporting_instance_approval_action": _policy(
        key="reporting.instance.approvals.edit",
        description="Approve or revoke an object for scoped instance export.",
        instance_scoped=True,
        requires_staff_or_system_admin=False,
    ),
    "reporting_instance_approval_bulk": _policy(
        key="reporting.instance.approvals.bulk",
        description="Bulk approve/revoke objects for scoped instance export.",
        instance_scoped=True,
        requires_staff_or_system_admin=False,
    ),
    "reporting_instance_consent": _policy(
        key="reporting.instance.consent.view",
        description="View consent workspace for scoped instance.",
        instance_scoped=True,
        requires_staff_or_system_admin=False,
    ),
    "reporting_instance_consent_action": _policy(
        key="reporting.instance.consent.edit",
        description="Apply consent decision for scoped instance object.",
        instance_scoped=True,
        requires_staff_or_system_admin=False,
    ),
    # Review/snapshots
    "reporting_instance_report_pack": _policy(
        key="reporting.instance.report_pack.view",
        description="View manager report pack for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_review": _policy(
        key="reporting.instance.review.view",
        description="View review dashboard for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_alignment_coverage": _policy(
        key="reporting.instance.alignment_coverage.view",
        description="View alignment coverage report for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_review_pack_v2": _policy(
        key="reporting.instance.review_pack_v2.view",
        description="View review pack v2 for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_review_decisions": _policy(
        key="reporting.instance.review_decisions.view",
        description="View review decisions for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_review_decision_create": _policy(
        key="reporting.instance.review_decisions.create",
        description="Create review decision for scoped instance snapshot.",
        instance_scoped=True,
    ),
    "reporting_instance_snapshots": _policy(
        key="reporting.instance.snapshots.view",
        description="View snapshots list for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_snapshot_create": _policy(
        key="reporting.instance.snapshots.create",
        description="Create snapshot for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_snapshot_detail": _policy(
        key="reporting.instance.snapshots.detail",
        description="View snapshot detail for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_snapshot_download": _policy(
        key="reporting.instance.snapshots.download",
        description="Download snapshot payload for scoped instance.",
        instance_scoped=True,
    ),
    "reporting_instance_snapshot_diff": _policy(
        key="reporting.instance.snapshots.diff",
        description="Compare snapshots for scoped instance.",
        instance_scoped=True,
    ),
}


def get_route_policy(view_name):
    return ROUTE_POLICY_REGISTRY.get(view_name)


def route_policy_matrix():
    return sorted(
        [
            {
                "view_name": view_name,
                "policy_key": policy.key,
                "description": policy.description,
                "instance_scoped": policy.instance_scoped,
                "instance_kwarg": policy.instance_kwarg,
                "requires_staff_or_system_admin": policy.requires_staff_or_system_admin,
                "no_leakage_expected": policy.no_leakage_expected,
            }
            for view_name, policy in ROUTE_POLICY_REGISTRY.items()
        ],
        key=lambda item: item["view_name"],
    )
