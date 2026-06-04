"""Tests for standalone username/password login.

Covers the PasswordLoginBackend (on/off, active/inactive, service-account
exclusion), admin-set passwords via the user form, and the self-service
change-password page.
"""

import pytest
from django.contrib.auth import authenticate
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import Permission, User
from apps.accounts.permissions import MANAGE_USERS

pytestmark = pytest.mark.django_db

GOOD_PASSWORD = "Sunflower-Garden-42"
NEW_PASSWORD = "Riverbed-Lantern-77"


# --- fixtures ---------------------------------------------------------------


@pytest.fixture
def regular_user():
    return User.objects.create_user(
        username="erin@turn5.local", email="erin@turn5.local", password=GOOD_PASSWORD
    )


@pytest.fixture
def manager():
    user = User.objects.create_user(username="mgr@turn5.local", email="mgr@turn5.local")
    Permission.objects.create(user=user, name=MANAGE_USERS)
    return user


@pytest.fixture
def claude_user():
    user, _ = User.objects.update_or_create(
        username="claude@turn5.local",
        defaults={
            "email": "claude@turn5.local",
            "role": User.ROLE_ADMIN,
            "is_claude_service": True,
        },
    )
    user.set_password(GOOD_PASSWORD)
    user.save()
    return user


# --- backend ----------------------------------------------------------------


def test_regular_user_can_log_in(client, regular_user):
    resp = client.post(
        "/accounts/login/", {"username": regular_user.username, "password": GOOD_PASSWORD}
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"
    assert client.get("/").status_code == 200  # session established


def test_wrong_password_is_rejected(client, regular_user):
    resp = client.post(
        "/accounts/login/", {"username": regular_user.username, "password": "not-it"}
    )
    assert resp.status_code == 200  # form re-rendered, not logged in
    assert client.get("/").status_code == 302  # still anonymous -> redirected


def test_inactive_user_cannot_log_in(client, regular_user):
    regular_user.is_active = False
    regular_user.save()
    assert authenticate(username=regular_user.username, password=GOOD_PASSWORD) is None


@override_settings(PASSWORD_LOGIN_ENABLED=False)
def test_password_login_disabled_blocks_regular_user(regular_user):
    assert authenticate(username=regular_user.username, password=GOOD_PASSWORD) is None


@override_settings(PASSWORD_LOGIN_ENABLED=False)
def test_service_account_still_logs_in_when_password_login_disabled(claude_user):
    # The Claude service account uses its own backend, independent of the flag.
    user = authenticate(username=claude_user.username, password=GOOD_PASSWORD)
    assert user is not None
    assert user.is_claude_service is True


def test_password_backend_excludes_service_account():
    from apps.accounts.auth_backends import PasswordLoginBackend

    svc, _ = User.objects.update_or_create(
        username="claude@turn5.local",
        defaults={"email": "claude@turn5.local", "is_claude_service": True},
    )
    svc.set_password(GOOD_PASSWORD)
    svc.save()
    # PasswordLoginBackend must refuse the service account even with right creds.
    assert (
        PasswordLoginBackend().authenticate(None, username=svc.username, password=GOOD_PASSWORD)
        is None
    )


# --- admin-set passwords via the user form ----------------------------------


def test_manager_creates_user_with_password_who_can_log_in(client, manager):
    client.force_login(manager)
    resp = client.post(
        reverse("user_create"),
        {
            "username": "newhire@turn5.local",
            "email": "newhire@turn5.local",
            "is_active": "on",
            "password1": GOOD_PASSWORD,
            "password2": GOOD_PASSWORD,
        },
    )
    assert resp.status_code == 302
    created = User.objects.get(username="newhire@turn5.local")
    assert created.has_usable_password()

    client.logout()
    login = client.post(
        "/accounts/login/", {"username": "newhire@turn5.local", "password": GOOD_PASSWORD}
    )
    assert login.status_code == 302  # the new user can sign in


def test_password_mismatch_is_rejected(client, manager):
    client.force_login(manager)
    resp = client.post(
        reverse("user_create"),
        {
            "username": "oops@turn5.local",
            "email": "oops@turn5.local",
            "is_active": "on",
            "password1": GOOD_PASSWORD,
            "password2": "different",
        },
    )
    assert resp.status_code == 200  # form invalid, re-rendered
    assert not User.objects.filter(username="oops@turn5.local").exists()


def test_weak_password_is_rejected(client, manager):
    client.force_login(manager)
    resp = client.post(
        reverse("user_create"),
        {
            "username": "weak@turn5.local",
            "email": "weak@turn5.local",
            "is_active": "on",
            "password1": "short",
            "password2": "short",
        },
    )
    assert resp.status_code == 200
    assert not User.objects.filter(username="weak@turn5.local").exists()


def test_edit_with_blank_password_keeps_existing(client, manager, regular_user):
    client.force_login(manager)
    resp = client.post(
        reverse("user_edit", args=[regular_user.pk]),
        {"username": regular_user.username, "email": "erin2@turn5.local", "is_active": "on"},
    )
    assert resp.status_code == 302
    regular_user.refresh_from_db()
    assert regular_user.email == "erin2@turn5.local"
    assert regular_user.check_password(GOOD_PASSWORD)  # password untouched


# --- self-service change password -------------------------------------------


def test_change_password_requires_login(client):
    resp = client.get(reverse("change_password"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


def test_user_changes_own_password_and_stays_logged_in(client, regular_user):
    client.force_login(regular_user)
    resp = client.post(
        reverse("change_password"),
        {
            "old_password": GOOD_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )
    assert resp.status_code == 302
    assert client.get("/").status_code == 200  # session preserved
    regular_user.refresh_from_db()
    assert regular_user.check_password(NEW_PASSWORD)


def test_change_password_wrong_old_password_fails(client, regular_user):
    client.force_login(regular_user)
    resp = client.post(
        reverse("change_password"),
        {"old_password": "wrong", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert resp.status_code == 200
    regular_user.refresh_from_db()
    assert regular_user.check_password(GOOD_PASSWORD)  # unchanged


@override_settings(PASSWORD_LOGIN_ENABLED=False)
def test_change_password_blocked_when_login_disabled(client, regular_user):
    client.force_login(regular_user)
    resp = client.get(reverse("change_password"))
    assert resp.status_code == 302  # bounced to profile
    assert resp.headers["Location"] == reverse("profile")


def test_profile_shows_change_password_link(client, regular_user):
    client.force_login(regular_user)
    resp = client.get(reverse("profile"))
    assert reverse("change_password").encode() in resp.content
