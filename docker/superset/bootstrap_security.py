import os

from superset.app import create_app
from superset.extensions import db


def clone_role(sm, target_name: str, source_name: str) -> None:
    source = sm.find_role(source_name)
    if source is None:
        raise RuntimeError(f"Superset source role '{source_name}' was not found.")
    role = sm.find_role(target_name)
    if role is None:
        role = sm.add_role(target_name)
    role.permissions = list(source.permissions)
    db.session.add(role)
    db.session.commit()


def ensure_admin_user(sm) -> None:
    username = os.getenv("SUPERSET_ADMIN_USERNAME", "admin").strip()
    password = os.getenv("SUPERSET_ADMIN_PASSWORD", "").strip()
    email = os.getenv("SUPERSET_ADMIN_EMAIL", "admin@example.org").strip()
    first_name = os.getenv("SUPERSET_ADMIN_FIRSTNAME", "NBMS").strip()
    last_name = os.getenv("SUPERSET_ADMIN_LASTNAME", "Admin").strip()
    admin_role = sm.find_role("Admin")
    if admin_role is None:
        raise RuntimeError("Superset Admin role is not available after 'superset init'.")

    user = sm.find_user(username=username)
    if user is None:
        if not password:
            raise RuntimeError("SUPERSET_ADMIN_PASSWORD must be set before running Superset init.")
        sm.add_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=admin_role,
            password=password,
        )
        return

    changed = False
    if user.email != email:
        user.email = email
        changed = True
    if user.first_name != first_name:
        user.first_name = first_name
        changed = True
    if user.last_name != last_name:
        user.last_name = last_name
        changed = True
    if admin_role not in list(user.roles):
        user.roles = [admin_role]
        changed = True
    if changed:
        db.session.add(user)
        db.session.commit()
    if password:
        sm.reset_password(user.id, password)


def main() -> None:
    app = create_app()
    with app.app_context():
        sm = app.appbuilder.sm
        ensure_admin_user(sm)
        clone_role(sm, "Publisher", "Alpha")
        clone_role(sm, "Stakeholder Viewer", "Gamma")
        print("Ensured Superset admin, Publisher, and Stakeholder Viewer roles.")


if __name__ == "__main__":
    main()
