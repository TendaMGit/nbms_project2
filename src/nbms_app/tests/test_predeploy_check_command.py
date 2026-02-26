import pytest
from django.core.management import CommandError, call_command as django_call_command

from nbms_app.management.commands import predeploy_check


REQUIRED_ENV = {
    "DJANGO_SECRET_KEY": "test-secret",
    "DATABASE_URL": "sqlite:///tmp-predeploy.sqlite3",
    "DJANGO_ALLOWED_HOSTS": "example.org",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.org",
}


def _set_required_env(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_predeploy_check_fails_when_required_env_missing(monkeypatch):
    for key in REQUIRED_ENV:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(CommandError, match="Missing required environment variables"):
        django_call_command("predeploy_check", skip_deploy_check=True, skip_migrate_check=True)


def test_predeploy_check_runs_deploy_and_migrate_checks(monkeypatch):
    _set_required_env(monkeypatch)
    calls = []

    def _fake_call_command(name, *args, **kwargs):
        calls.append((name, kwargs))

    monkeypatch.setattr(predeploy_check, "call_command", _fake_call_command)

    django_call_command("predeploy_check")

    assert [name for name, _kwargs in calls] == ["check", "migrate"]
    assert calls[0][1]["deploy"] is True
    assert calls[1][1]["check"] is True


def test_predeploy_check_reports_unapplied_migrations(monkeypatch):
    _set_required_env(monkeypatch)

    def _fake_call_command(name, *args, **kwargs):
        if name == "migrate":
            raise SystemExit(1)
        return None

    monkeypatch.setattr(predeploy_check, "call_command", _fake_call_command)

    with pytest.raises(CommandError, match="Unapplied migrations"):
        django_call_command("predeploy_check")
