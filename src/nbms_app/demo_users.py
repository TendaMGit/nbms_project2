from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth.models import Group
from django.core.management import call_command

from nbms_app.models import (
    MonitoringProgramme,
    MonitoringProgrammeSteward,
    Organisation,
    ProgrammeStewardRole,
    User,
)


WARNING_BANNER = "FOR LOCAL DEV/DEMO ONLY - DO NOT USE IN PRODUCTION"


DEMO_ORGANISATIONS = [
    {"org_code": "SANBI", "name": "South African National Biodiversity Institute", "org_type": "Government"},
    {"org_code": "DFFE", "name": "Department of Forestry, Fisheries and the Environment", "org_type": "Government"},
    {"org_code": "STATS-SA", "name": "Statistics South Africa", "org_type": "Government"},
    {"org_code": "SAEON", "name": "South African Environmental Observation Network", "org_type": "Research"},
    {"org_code": "IPLC", "name": "Indigenous Peoples and Local Communities", "org_type": "Community"},
    {"org_code": "DEMOORG", "name": "NBMS Demo Organisation", "org_type": "Other"},
]


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    org_code: str
    groups: tuple[str, ...]
    is_staff: bool = True
    is_superuser: bool = False
    first_name: str = ""
    last_name: str = ""
    email: str = ""


DEMO_USER_SPECS = [
    DemoUserSpec("Contributor", "SANBI", ("Contributor",), first_name="Demo", last_name="Contributor"),
    DemoUserSpec("IndicatorLead", "SANBI", ("Indicator Lead",), first_name="Demo", last_name="Indicator Lead"),
    DemoUserSpec("ProgrammeSteward", "SAEON", ("Data Steward",), first_name="Demo", last_name="Programme Steward"),
    DemoUserSpec("DatasetSteward", "STATS-SA", ("Data Steward",), first_name="Demo", last_name="Dataset Steward"),
    DemoUserSpec("Reviewer", "DFFE", ("Secretariat",), first_name="Demo", last_name="Reviewer"),
    DemoUserSpec("Approver", "DFFE", ("Admin",), first_name="Demo", last_name="Approver"),
    DemoUserSpec("Publisher", "DFFE", ("Admin",), first_name="Demo", last_name="Publisher"),
    DemoUserSpec("RamsarFocalPoint", "DFFE", ("Secretariat",), first_name="Demo", last_name="Ramsar Focal Point"),
    DemoUserSpec("CITESFocalPoint", "DFFE", ("Secretariat",), first_name="Demo", last_name="CITES Focal Point"),
    DemoUserSpec("CMSFocalPoint", "DFFE", ("Secretariat",), first_name="Demo", last_name="CMS Focal Point"),
    DemoUserSpec("Auditor", "SANBI", ("Security Officer",), first_name="Demo", last_name="Auditor"),
    DemoUserSpec("IPLCRepresentative", "IPLC", ("Community Representative",), first_name="Demo", last_name="IPLC Rep"),
    DemoUserSpec("PublicUser", "DEMOORG", ("Viewer",), is_staff=False, first_name="Demo", last_name="Public"),
]


def ensure_demo_organisations():
    organisations = {}
    for item in DEMO_ORGANISATIONS:
        org = Organisation.objects.filter(org_code=item["org_code"]).order_by("id").first()
        if org is None:
            org = Organisation.objects.filter(name=item["name"]).order_by("id").first()
        if org is None:
            org = Organisation(org_code=item["org_code"])
        org.org_code = item["org_code"]
        org.name = item["name"]
        org.org_type = item["org_type"]
        org.is_active = True
        org.source_system = "nbms_demo_seed"
        org.source_ref = "seed_demo_users"
        org.save()
        organisations[item["org_code"]] = org
    return organisations


def _ensure_group(name: str):
    group, _ = Group.objects.get_or_create(name=name)
    return group


def seed_demo_user_pack(*, allow_insecure_passwords: bool):
    if not allow_insecure_passwords:
        raise ValueError("allow_insecure_passwords must be True for demo user seeding.")

    call_command("bootstrap_roles", verbosity=0)
    organisations = ensure_demo_organisations()
    rows = []
    users_by_username = {}

    for spec in DEMO_USER_SPECS:
        organisation = organisations[spec.org_code]
        email = spec.email or f"{spec.username.lower()}@demo.nbms.local"
        user, created = User.objects.get_or_create(
            username=spec.username,
            defaults={
                "email": email,
                "first_name": spec.first_name,
                "last_name": spec.last_name,
                "organisation": organisation,
                "is_staff": spec.is_staff,
                "is_superuser": spec.is_superuser,
                "is_active": True,
            },
        )
        user.email = email
        user.first_name = spec.first_name
        user.last_name = spec.last_name
        user.organisation = organisation
        user.is_staff = spec.is_staff
        user.is_superuser = spec.is_superuser
        user.is_active = True
        user.set_password(spec.username)
        user.save()
        group_ids = []
        for group_name in spec.groups:
            group_ids.append(_ensure_group(group_name).id)
        user.groups.set(Group.objects.filter(id__in=group_ids).order_by("name", "id"))
        users_by_username[spec.username] = user
        rows.append(
            {
                "username": user.username,
                "password": spec.username,
                "org": organisation.org_code or organisation.name,
                "groups_or_roles": ", ".join(sorted(spec.groups)),
                "staff": "yes" if user.is_staff else "no",
                "superuser": "yes" if user.is_superuser else "no",
                "created": created,
            }
        )

    steward_user = users_by_username.get("ProgrammeSteward")
    if steward_user:
        programmes = MonitoringProgramme.objects.filter(
            programme_code__in=["NBMS-SPATIAL-BASELINES", "NBMS-BIRDIE-INTEGRATION", "NBMS-CORE-PROGRAMME"]
        ).order_by("programme_code", "id")
        for programme in programmes:
            MonitoringProgrammeSteward.objects.update_or_create(
                programme=programme,
                user=steward_user,
                role=ProgrammeStewardRole.OPERATOR,
                defaults={"is_active": True, "is_primary": True},
            )

    return sorted(rows, key=lambda item: item["username"].lower())


def list_demo_user_rows():
    users = {user.username: user for user in User.objects.filter(username__in=[spec.username for spec in DEMO_USER_SPECS])}
    rows = []
    for spec in DEMO_USER_SPECS:
        user = users.get(spec.username)
        if not user:
            continue
        rows.append(
            {
                "username": user.username,
                "password": spec.username,
                "org": user.organisation.org_code if user.organisation_id else "",
                "groups_or_roles": ", ".join(user.groups.order_by("name", "id").values_list("name", flat=True)),
                "staff": "yes" if user.is_staff else "no",
                "superuser": "yes" if user.is_superuser else "no",
                "created": False,
            }
        )
    return sorted(rows, key=lambda item: item["username"].lower())


def markdown_table(rows):
    header = "| username | password | org | groups/roles | staff? | superuser? |"
    divider = "|---|---|---|---|---|---|"
    body = [
        f"| {row['username']} | {row['password']} | {row['org']} | {row['groups_or_roles']} | {row['staff']} | {row['superuser']} |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def csv_table(rows):
    lines = ["username,password,org,groups_roles,staff,superuser"]
    for row in rows:
        values = [
            row["username"],
            row["password"],
            row["org"],
            row["groups_or_roles"].replace(",", ";"),
            row["staff"],
            row["superuser"],
        ]
        lines.append(",".join(values))
    return "\n".join(lines) + "\n"


def write_demo_users_markdown(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = [
        f"# {WARNING_BANNER}",
        "",
        "This file is generated by `python manage.py seed_demo_users`.",
        "",
        markdown_table(rows),
        "",
    ]
    path.write_text("\n".join(content), encoding="utf-8")
