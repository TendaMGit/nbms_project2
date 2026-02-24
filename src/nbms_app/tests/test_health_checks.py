import pytest
from django.urls import reverse

from nbms_app import views


pytestmark = pytest.mark.django_db


def test_healthz_returns_ok(client):
    response = client.get(reverse("nbms_app:healthz"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_returns_ready_when_checks_pass(client, monkeypatch):
    monkeypatch.setattr(views, "_database_available", lambda: None)
    monkeypatch.setattr(views, "_pending_migrations", lambda: False)

    response = client.get(reverse("nbms_app:readyz"))

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "migrations": "ok"}}


def test_readyz_returns_not_ready_for_pending_migrations(client, monkeypatch):
    monkeypatch.setattr(views, "_database_available", lambda: None)
    monkeypatch.setattr(views, "_pending_migrations", lambda: True)

    response = client.get(reverse("nbms_app:readyz"))

    assert response.status_code == 503
    assert response.json()["checks"]["migrations"] == "pending"


def test_readyz_returns_not_ready_when_database_check_fails(client, monkeypatch):
    def _raise_db_error():
        raise RuntimeError("db down")

    monkeypatch.setattr(views, "_database_available", _raise_db_error)

    response = client.get(reverse("nbms_app:readyz"))

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not-ready"
    assert payload["checks"]["database"] == "error"
