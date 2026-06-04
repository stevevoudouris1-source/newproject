"""Tests for the user-management UI and its permission gating.

Covers the three required angles (auth, authz, happy path) plus the read-only
(VIEW_USERS) vs. manage (MANAGE_USERS) distinction and deny-by-default scoping.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import Permission, User
from apps.accounts.permissions import MANAGE_USERS, VIEW_USERS, PermissionsCatalog

pytestmark = pytest.mark.django_db


# --- fixtures ---------------------------------------------------------------


def _make_user(username, role=User.ROLE_MEMBER, **grants):
    user = User.objects.create_user(username=username, email=f"{username}@turn5.local", role=role)
    for name, granted in grants.items():
        if granted:
            Permission.objects.create(
                user=user, name={"view": VIEW_USERS, "manage": MANAGE_USERS}[name]
            )
    return user


@pytest.fixture
def member_user():
    # Local copy of the tests/conftest.py fixture (that conftest only applies to
    # the tests/ tree, not apps/). A plain member with no grants.
    return _make_user("member")


@pytest.fixture
def claude_user():
    # The provisioning migration may already have created this row in the test
    # DB; update_or_create keeps the fixture idempotent.
    user, _ = User.objects.update_or_create(
        username="claude@turn5.local",
        defaults={
            "email": "claude@turn5.local",
            "role": User.ROLE_ADMIN,
            "is_claude_service": True,
        },
    )
    return user


@pytest.fixture
def viewer():
    return _make_user("viewer", view=True)


@pytest.fixture
def manager():
    return _make_user("manager", view=True, manage=True)


@pytest.fixture
def admin():
    return _make_user("boss", role=User.ROLE_ADMIN)


# --- catalog ----------------------------------------------------------------


def test_view_users_is_registered():
    assert "view_users" in PermissionsCatalog.all()


# --- auth gating ------------------------------------------------------------


def test_user_list_requires_login(client):
    resp = client.get(reverse("user_list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.headers["Location"]


def test_user_list_denied_without_permission(client, member_user):
    client.force_login(member_user)
    assert client.get(reverse("user_list")).status_code == 403


def test_user_detail_denied_without_permission(client, member_user):
    client.force_login(member_user)
    assert client.get(reverse("user_detail", args=[member_user.pk])).status_code == 403


# --- read-only access (VIEW_USERS) ------------------------------------------


def test_viewer_can_list_and_view(client, viewer, member_user):
    client.force_login(viewer)
    resp = client.get(reverse("user_list"))
    assert resp.status_code == 200
    assert b"member@turn5.local" in resp.content  # sees other accounts

    detail = client.get(reverse("user_detail", args=[member_user.pk]))
    assert detail.status_code == 200


def test_viewer_cannot_create_or_edit(client, viewer, member_user):
    client.force_login(viewer)
    assert client.get(reverse("user_create")).status_code == 403
    assert client.get(reverse("user_edit", args=[member_user.pk])).status_code == 403


def test_viewer_sees_users_nav_link(client, viewer):
    client.force_login(viewer)
    resp = client.get(reverse("index"))
    assert reverse("user_list").encode() in resp.content


def test_member_does_not_see_users_nav_link(client, member_user):
    client.force_login(member_user)
    resp = client.get(reverse("index"))
    assert reverse("user_list").encode() not in resp.content


# --- manage access (MANAGE_USERS) -------------------------------------------


def test_manager_can_open_create_form(client, manager):
    client.force_login(manager)
    assert client.get(reverse("user_create")).status_code == 200


def test_manager_creates_user_with_view_only_grant(client, manager):
    client.force_login(manager)
    resp = client.post(
        reverse("user_create"),
        {
            "username": "newbie",
            "email": "newbie@turn5.local",
            "is_active": "on",
            "can_view_users": "on",
        },
    )
    assert resp.status_code == 302
    created = User.objects.get(username="newbie")
    assert created.can(VIEW_USERS) is True
    assert created.can(MANAGE_USERS) is False


def test_manage_grant_implies_view_grant(client, manager):
    client.force_login(manager)
    # Tick only "manage"; the view grant must be created alongside it.
    client.post(
        reverse("user_create"),
        {
            "username": "mgr2",
            "email": "mgr2@turn5.local",
            "is_active": "on",
            "can_manage_users": "on",
        },
    )
    created = User.objects.get(username="mgr2")
    assert created.can(MANAGE_USERS) is True
    assert created.can(VIEW_USERS) is True


def test_manager_edits_user_and_revokes_grant(client, manager):
    target = _make_user("editme", view=True)
    assert target.can(VIEW_USERS) is True
    client.force_login(manager)
    # Submit the edit form with both boxes unchecked -> grant removed.
    resp = client.post(
        reverse("user_edit", args=[target.pk]),
        {"username": "editme", "email": "changed@turn5.local", "is_active": "on"},
    )
    assert resp.status_code == 302
    target.refresh_from_db()
    assert target.email == "changed@turn5.local"
    assert target.can(VIEW_USERS) is False


def test_claude_service_account_cannot_be_edited_here(client, manager, claude_user):
    client.force_login(manager)
    resp = client.post(
        reverse("user_edit", args=[claude_user.pk]),
        {"username": claude_user.username, "email": "hacked@turn5.local", "is_active": "on"},
    )
    assert resp.status_code == 302  # redirected, not applied
    claude_user.refresh_from_db()
    assert claude_user.email != "hacked@turn5.local"


# --- admin & scoping --------------------------------------------------------


def test_admin_has_full_access(client, admin):
    client.force_login(admin)
    assert client.get(reverse("user_list")).status_code == 200
    assert client.get(reverse("user_create")).status_code == 200


def test_for_user_scoping_denies_members_and_allows_viewers(member_user, viewer):
    # A plain member sees no user rows; a viewer sees everyone.
    assert User.objects.for_user(member_user).count() == 0
    assert User.objects.for_user(viewer).count() == User.objects.count()
