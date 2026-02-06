import ast
import inspect
from pathlib import Path

import pytest

from nbms_app import views
from nbms_app.services.policy_registry import ROUTE_POLICY_REGISTRY, route_policy_matrix


pytestmark = pytest.mark.django_db


def _staff_decorated_view_names():
    source_path = Path("src/nbms_app/views.py")
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    names = []
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "staff_or_system_admin_required":
                names.append(node.name)
                break
    return sorted(names)


def test_staff_decorated_views_have_policy_entries():
    decorated = _staff_decorated_view_names()
    missing = [name for name in decorated if name not in ROUTE_POLICY_REGISTRY]
    assert not missing, f"Missing route policy entries for: {', '.join(missing)}"


def test_instance_scoped_policies_match_view_signatures():
    errors = []
    for view_name, policy in ROUTE_POLICY_REGISTRY.items():
        if not policy.instance_scoped:
            continue
        view_func = getattr(views, view_name, None)
        if view_func is None:
            errors.append(f"{view_name}: view function not found")
            continue
        signature = inspect.signature(view_func)
        if policy.instance_kwarg not in signature.parameters:
            errors.append(
                f"{view_name}: instance_kwarg '{policy.instance_kwarg}' missing from signature {signature}"
            )
    assert not errors, "\n".join(errors)


def test_policy_matrix_is_deterministic_and_covers_critical_routes():
    matrix = route_policy_matrix()
    assert matrix == sorted(matrix, key=lambda row: row["view_name"])

    view_names = {row["view_name"] for row in matrix}
    critical = {
        "reporting_instance_sections",
        "reporting_instance_section_i",
        "reporting_instance_section_ii",
        "reporting_instance_section_iii",
        "reporting_instance_section_iv",
        "reporting_instance_section_v",
        "reporting_instance_approvals",
        "reporting_instance_consent",
        "reporting_instance_snapshots",
        "reporting_instance_review",
        "reporting_instance_review_decision_create",
        "export_ort_nr7_v2_instance",
    }
    assert critical.issubset(view_names)
