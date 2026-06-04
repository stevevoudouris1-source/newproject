"""Smoke tests: health, auth gating, hello world, key pages render."""

import pytest
from django.test import override_settings


def test_health_check_no_auth(client):
    resp = client.get("/up/")
    assert resp.status_code == 200
    assert resp.content == b"OK"


@pytest.mark.django_db
def test_index_requires_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


@pytest.mark.django_db
def test_index_says_hello_when_logged_in(client, member_user):
    client.force_login(member_user)
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Hello, member@turn5.local!" in resp.content


@pytest.mark.django_db
def test_login_page_renders(client):
    resp = client.get("/accounts/login/")
    assert resp.status_code == 200
    # The username/password form is the default sign-in path.
    assert b'name="username"' in resp.content
    assert b'name="password"' in resp.content


@pytest.mark.django_db
def test_login_page_hides_microsoft_button_when_oidc_disabled(client):
    # OIDC is unconfigured in dev/test, so SSO must not be offered.
    resp = client.get("/accounts/login/")
    assert b"Sign in with Microsoft" not in resp.content


@override_settings(OIDC_ENABLED=True)
@pytest.mark.django_db
def test_login_page_shows_microsoft_button_when_oidc_enabled(client):
    resp = client.get("/accounts/login/")
    assert b"Sign in with Microsoft" in resp.content


@pytest.mark.django_db
def test_profile_requires_login(client):
    resp = client.get("/accounts/profile/")
    assert resp.status_code == 302
