from __future__ import annotations

from dataclasses import dataclass

from nbms_app.demo_users import DEMO_USER_SPECS
from nbms_app.services.capabilities import user_capabilities


@dataclass(frozen=True)
class UiSurface:
    label: str
    route: str
    capability: str | None
    public: bool = False


UI_SURFACES = [
    UiSurface(label="Dashboard", route="/dashboard", capability="can_view_dashboard"),
    UiSurface(label="Indicator Explorer", route="/indicators", capability=None, public=True),
    UiSurface(label="Spatial Viewer", route="/map", capability="can_view_spatial"),
    UiSurface(label="Programme Ops", route="/programmes", capability="can_view_programmes"),
    UiSurface(label="Programme Templates", route="/programmes/templates", capability="can_manage_programme_templates"),
    UiSurface(label="BIRDIE", route="/programmes/birdie", capability="can_view_birdie"),
    UiSurface(label="Ecosystem Registry", route="/registries/ecosystems", capability="can_view_registries"),
    UiSurface(label="Taxon Registry", route="/registries/taxa", capability="can_view_registries"),
    UiSurface(label="IAS Registry", route="/registries/ias", capability="can_view_registries"),
    UiSurface(label="NR7 Builder", route="/nr7-builder", capability="can_view_reporting_builder"),
    UiSurface(label="MEA Packs", route="/template-packs", capability="can_view_template_packs"),
    UiSurface(label="Report Products", route="/report-products", capability="can_view_report_products"),
    UiSurface(label="System Health", route="/system-health", capability="can_view_system_health"),
]


def demo_role_matrix(users_by_username):
    rows = []
    for spec in DEMO_USER_SPECS:
        user = users_by_username.get(spec.username)
        if not user:
            continue
        capabilities = user_capabilities(user)
        visible_routes = []
        for surface in UI_SURFACES:
            if surface.public:
                visible_routes.append(surface.route)
            elif surface.capability and capabilities.get(surface.capability):
                visible_routes.append(surface.route)
        rows.append(
            {
                "username": spec.username,
                "org_code": user.organisation.org_code if user.organisation_id else "",
                "groups": "; ".join(user.groups.order_by("name", "id").values_list("name", flat=True)),
                "is_staff": "yes" if user.is_staff else "no",
                "is_superuser": "yes" if user.is_superuser else "no",
                "visible_routes": "; ".join(visible_routes),
            }
        )
    return rows
