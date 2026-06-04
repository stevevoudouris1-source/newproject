"""Authentication: the Claude service-account password backend."""

import pytest

from apps.accounts.auth_backends import ClaudeServiceBackend


@pytest.mark.django_db
def test_service_backend_accepts_claude(claude_user, claude_password):
    backend = ClaudeServiceBackend()
    result = backend.authenticate(None, username="claude@turn5.local", password=claude_password)
    assert result == claude_user


@pytest.mark.django_db
def test_service_backend_rejects_wrong_password(claude_user):
    backend = ClaudeServiceBackend()
    assert backend.authenticate(None, username="claude@turn5.local", password="nope") is None


@pytest.mark.django_db
def test_service_backend_refuses_non_service_user(member_user):
    """A normal user's password must never authenticate via this backend."""
    backend = ClaudeServiceBackend()
    result = backend.authenticate(
        None, username="member@turn5.local", password="member-password-1234567890ABcd"
    )
    assert result is None


@pytest.mark.django_db
def test_service_login_renders_hello(client, claude_user, claude_password):
    resp = client.post(
        "/accounts/login/?service=true",
        {"username": "claude@turn5.local", "password": claude_password},
    )
    assert resp.status_code == 302  # successful login redirects to "/"
    followed = client.get("/")
    assert followed.status_code == 200
    assert b"Hello, claude@turn5.local!" in followed.content


@pytest.mark.django_db
def test_claude_account_provisioned_by_migration():
    """The data migration created the service account (unusable pw until set)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.get(username="claude@turn5.local")
    assert user.is_claude_service is True
    assert user.role == User.ROLE_ADMIN
    assert user.is_staff is True
    assert user.is_superuser is False
