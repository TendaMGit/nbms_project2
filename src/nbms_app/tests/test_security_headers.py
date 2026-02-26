import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from nbms_app.models import Organisation, User


pytestmark = pytest.mark.django_db


@override_settings(
    CONTENT_SECURITY_POLICY="default-src 'self';",
    CONTENT_SECURITY_POLICY_REPORT_ONLY=False,
    SECURE_CONTENT_TYPE_NOSNIFF=True,
    SECURE_REFERRER_POLICY="strict-origin-when-cross-origin",
    X_FRAME_OPTIONS="DENY",
    PERMISSIONS_POLICY="geolocation=(), camera=()",
    SECURE_CROSS_ORIGIN_OPENER_POLICY="same-origin",
)
def test_security_headers_present_on_health_endpoint(client):
    response = client.get(reverse("nbms_app:health_db"))

    assert response.status_code == 200
    assert response["Content-Security-Policy"].startswith("default-src")
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Permissions-Policy"] == "geolocation=(), camera=()"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"


@override_settings(
    CONTENT_SECURITY_POLICY="default-src 'self';",
    CONTENT_SECURITY_POLICY_REPORT_ONLY=True,
)
def test_csp_report_only_header_mode(client):
    response = client.get(reverse("nbms_app:health_db"))

    assert response.status_code == 200
    assert "Content-Security-Policy-Report-Only" in response
    assert "Content-Security-Policy" not in response


@override_settings(
    SESSION_COOKIE_NAME="nbms_sessionid",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    CSRF_COOKIE_SECURE=True,
    CSRF_COOKIE_HTTPONLY=True,
    CSRF_COOKIE_SAMESITE="Lax",
)
def test_session_and_csrf_cookie_flags_are_hardened(client):
    org = Organisation.objects.create(name="Org", org_code="ORG")
    user = User.objects.create_user(username="secure-user", password="Pass_12345", organisation=org)

    login_response = client.post(reverse("login"), {"username": user.username, "password": "Pass_12345"})
    assert login_response.status_code in {302, 200}

    assert settings.SESSION_COOKIE_NAME in login_response.cookies
    session_cookie = login_response.cookies[settings.SESSION_COOKIE_NAME]
    assert bool(session_cookie["secure"])
    assert bool(session_cookie["httponly"])
    assert session_cookie["samesite"] == "Lax"

    csrf_response = client.get(reverse("api_auth_csrf"))
    assert settings.CSRF_COOKIE_NAME in csrf_response.cookies
    csrf_cookie = csrf_response.cookies[settings.CSRF_COOKIE_NAME]
    assert bool(csrf_cookie["secure"])
    assert bool(csrf_cookie["httponly"])
    assert csrf_cookie["samesite"] == "Lax"
