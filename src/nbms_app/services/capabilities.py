from __future__ import annotations

from nbms_app.services.authorization import (
    ROLE_ADMIN,
    ROLE_CONTRIBUTOR,
    ROLE_DATA_STEWARD,
    ROLE_INDICATOR_LEAD,
    ROLE_PUBLISHING_AUTHORITY,
    ROLE_SECRETARIAT,
    ROLE_SECTION_LEAD,
    ROLE_TECHNICAL_COMMITTEE,
    is_system_admin,
    user_has_role,
)


def user_capabilities(user):
    is_authenticated = bool(user and getattr(user, "is_authenticated", False))
    is_staff = bool(getattr(user, "is_staff", False))
    can_author_reports = bool(
        is_system_admin(user)
        or user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN, ROLE_SECTION_LEAD)
    )
    can_view_programmes = bool(
        is_system_admin(user)
        or user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD)
    )
    can_technical_signoff = bool(is_system_admin(user) or user_has_role(user, ROLE_TECHNICAL_COMMITTEE, ROLE_ADMIN))
    can_publishing_approve = bool(
        is_system_admin(user)
        or user_has_role(user, ROLE_PUBLISHING_AUTHORITY, ROLE_SECRETARIAT, ROLE_ADMIN)
    )
    return {
        "is_staff": is_staff,
        "is_system_admin": bool(is_system_admin(user)),
        "can_manage_exports": bool(user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)),
        "can_review": bool(user_has_role(user, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_ADMIN)),
        "can_publish": bool(user_has_role(user, ROLE_SECRETARIAT, ROLE_ADMIN) or is_system_admin(user)),
        "can_edit_indicators": bool(
            user_has_role(user, ROLE_INDICATOR_LEAD, ROLE_DATA_STEWARD, ROLE_SECRETARIAT, ROLE_ADMIN)
            or is_system_admin(user)
        ),
        "can_view_dashboard": is_authenticated,
        "can_view_spatial": is_authenticated,
        "can_view_programmes": is_authenticated and can_view_programmes,
        "can_view_birdie": is_authenticated and can_view_programmes,
        "can_view_reporting_builder": is_authenticated and can_author_reports,
        "can_view_template_packs": is_authenticated and can_author_reports,
        "can_view_report_products": is_authenticated and can_author_reports,
        "can_view_national_report_workspace": is_authenticated and can_author_reports,
        "can_section_review": is_authenticated
        and bool(is_system_admin(user) or user_has_role(user, ROLE_SECTION_LEAD, ROLE_SECRETARIAT, ROLE_ADMIN)),
        "can_technical_signoff": is_authenticated and can_technical_signoff,
        "can_publishing_approve": is_authenticated and can_publishing_approve,
        "can_view_registries": is_authenticated,
        "can_manage_registry_workflows": bool(
            is_authenticated and (is_system_admin(user) or user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_DATA_STEWARD, ROLE_INDICATOR_LEAD))
        ),
        "can_manage_programme_templates": bool(
            is_authenticated and (is_system_admin(user) or user_has_role(user, ROLE_ADMIN, ROLE_SECRETARIAT, ROLE_DATA_STEWARD))
        ),
        "can_view_system_health": is_authenticated and bool(is_system_admin(user) or user_has_role(user, ROLE_ADMIN)),
        "can_contribute": bool(is_authenticated and user_has_role(user, ROLE_CONTRIBUTOR)),
    }
