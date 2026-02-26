import pytest
from django.contrib.auth import authenticate
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from nbms_app.demo_users import DEMO_USER_SPECS
from nbms_app.models import (
    Indicator,
    LifecycleStatus,
    NationalIndicatorType,
    NationalTarget,
    Organisation,
    SensitivityLevel,
    User,
)


pytestmark = pytest.mark.django_db


def test_ensure_system_admin_requires_env(monkeypatch):
    monkeypatch.delenv("NBMS_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("NBMS_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("NBMS_ADMIN_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("ensure_system_admin")


def test_ensure_system_admin_is_idempotent(monkeypatch):
    monkeypatch.setenv("NBMS_ADMIN_USERNAME", "SystemAdminLocal")
    monkeypatch.setenv("NBMS_ADMIN_EMAIL", "system.admin@example.org")
    monkeypatch.setenv("NBMS_ADMIN_PASSWORD", "AdminPass#123")
    call_command("ensure_system_admin")
    call_command("ensure_system_admin")

    user = User.objects.get(username="SystemAdminLocal")
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
    assert user.groups.filter(name="SystemAdmin").exists()
    assert user.has_perm("nbms_app.system_admin")
    assert authenticate(username="SystemAdminLocal", password="AdminPass#123")


def test_seed_demo_users_gated(monkeypatch):
    monkeypatch.setenv("SEED_DEMO_USERS", "0")
    monkeypatch.setenv("ALLOW_INSECURE_DEMO_PASSWORDS", "0")
    with pytest.raises(CommandError):
        call_command("seed_demo_users")


def test_seed_demo_users_reconciles_existing_org_name_conflicts(monkeypatch, tmp_path):
    Organisation.objects.create(
        org_code="STATSSA",
        name="Statistics South Africa",
        org_type="Government",
    )
    monkeypatch.setenv("SEED_DEMO_USERS", "1")
    monkeypatch.setenv("ALLOW_INSECURE_DEMO_PASSWORDS", "1")

    call_command("seed_demo_users", "--output", str(tmp_path / "DEMO_USERS.md"))

    org = Organisation.objects.get(name="Statistics South Africa")
    assert org.org_code == "STATS-SA"
    assert Organisation.objects.filter(name="Statistics South Africa").count() == 1


def test_seed_demo_users_writes_output_and_role_surfaces(monkeypatch, tmp_path, client):
    monkeypatch.setenv("SEED_DEMO_USERS", "1")
    monkeypatch.setenv("ALLOW_INSECURE_DEMO_PASSWORDS", "1")
    output = tmp_path / "DEMO_USERS.md"

    call_command("seed_demo_users", "--output", str(output))
    call_command("seed_demo_users", "--output", str(output))
    assert output.exists()
    assert "FOR LOCAL DEV/DEMO ONLY - DO NOT USE IN PRODUCTION" in output.read_text(encoding="utf-8")

    usernames = [item.username for item in DEMO_USER_SPECS]
    assert User.objects.filter(username__in=usernames).count() == len(usernames)
    for username in usernames:
        assert authenticate(username=username, password=username)

    sanbi = Organisation.objects.get(org_code="SANBI")
    dffe = Organisation.objects.get(org_code="DFFE")
    public_user = User.objects.get(username="PublicUser")
    contributor = User.objects.get(username="Contributor")
    reviewer = User.objects.get(username="Reviewer")

    target_sanbi = NationalTarget.objects.create(
        code="ZA-DEMO-T1",
        title="Demo SANBI target",
        organisation=sanbi,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    target_dffe = NationalTarget.objects.create(
        code="ZA-DEMO-T2",
        title="Demo DFFE target",
        organisation=dffe,
        status=LifecycleStatus.PUBLISHED,
        sensitivity=SensitivityLevel.PUBLIC,
    )
    draft_indicator = Indicator.objects.create(
        code="DEMO-DRAFT-1",
        title="Draft indicator",
        national_target=target_sanbi,
        organisation=sanbi,
        created_by=contributor,
        indicator_type=NationalIndicatorType.OTHER,
        status=LifecycleStatus.DRAFT,
        sensitivity=SensitivityLevel.INTERNAL,
    )
    Indicator.objects.create(
        code="DEMO-REVIEW-1",
        title="Review indicator",
        national_target=target_dffe,
        organisation=dffe,
        created_by=reviewer,
        indicator_type=NationalIndicatorType.OTHER,
        status=LifecycleStatus.PENDING_REVIEW,
        sensitivity=SensitivityLevel.INTERNAL,
    )

    assert client.login(username=public_user.username, password=public_user.username)
    public_list = client.get(reverse("api_indicator_list"))
    assert public_list.status_code == 200
    public_codes = [row["code"] for row in public_list.json()["results"]]
    assert draft_indicator.code not in public_codes
    client.logout()

    assert client.login(username=contributor.username, password=contributor.username)
    contributor_me = client.get(reverse("api_auth_me"))
    assert contributor_me.status_code == 200
    assert contributor_me.json()["capabilities"]["can_review"] is False
    contributor_codes = [row["code"] for row in client.get(reverse("api_indicator_list")).json()["results"]]
    assert draft_indicator.code in contributor_codes
    client.logout()

    assert client.login(username=reviewer.username, password=reviewer.username)
    reviewer_me = client.get(reverse("api_auth_me"))
    assert reviewer_me.status_code == 200
    assert reviewer_me.json()["capabilities"]["can_review"] is True
    dashboard = client.get(reverse("api_dashboard_summary"))
    assert dashboard.status_code == 200
    assert dashboard.json()["approvals_queue"] >= 1


def test_list_demo_users_outputs_table(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("SEED_DEMO_USERS", "1")
    monkeypatch.setenv("ALLOW_INSECURE_DEMO_PASSWORDS", "1")
    call_command("seed_demo_users", "--output", str(tmp_path / "DEMO_USERS.md"))
    call_command("list_demo_users")
    captured = capsys.readouterr().out
    assert "| username | password | org | groups/roles | staff? | superuser? |" in captured


def test_issue_e2e_sessions_returns_valid_keys(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("SEED_DEMO_USERS", "1")
    monkeypatch.setenv("ALLOW_INSECURE_DEMO_PASSWORDS", "1")
    call_command("seed_demo_users", "--output", str(tmp_path / "DEMO_USERS.md"))

    call_command("issue_e2e_sessions", "--users", "Contributor", "Reviewer")
    payload = capsys.readouterr().out.strip().splitlines()[-1]

    import json

    sessions = json.loads(payload)
    assert "Contributor" in sessions
    assert "Reviewer" in sessions
    assert Session.objects.filter(session_key=sessions["Contributor"]).exists()
    assert Session.objects.filter(session_key=sessions["Reviewer"]).exists()
