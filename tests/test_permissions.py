"""Authorization: deny-by-default, grants, and the pagination cap."""

import pytest
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Permission
from apps.accounts.permissions import MANAGE_USERS, authorize, can
from apps.common.pagination import safe_limit


@pytest.mark.django_db
def test_member_denied_by_default(member_user):
    assert can(member_user, MANAGE_USERS) is False
    with pytest.raises(PermissionDenied):
        authorize(member_user, MANAGE_USERS)


@pytest.mark.django_db
def test_admin_allowed(claude_user):
    assert can(claude_user, MANAGE_USERS) is True
    assert authorize(claude_user, MANAGE_USERS) is True


@pytest.mark.django_db
def test_member_with_global_grant(member_user):
    Permission.objects.create(user=member_user, name=MANAGE_USERS)
    assert can(member_user, MANAGE_USERS) is True


@pytest.mark.django_db
def test_per_object_grant_does_not_leak_to_global_check(member_user):
    """A grant scoped to one object must not satisfy a global permission check."""
    Permission.objects.create(
        user=member_user, name=MANAGE_USERS, resource_type="User", resource_id=999
    )
    assert can(member_user, MANAGE_USERS) is False


def test_anonymous_is_denied():
    class Anon:
        is_authenticated = False

    assert can(Anon(), MANAGE_USERS) is False
    with pytest.raises(PermissionDenied):
        authorize(Anon(), MANAGE_USERS)


def test_safe_limit_clamps():
    assert safe_limit("10") == 10
    assert safe_limit("9999") == 100  # hard cap
    assert safe_limit("0") == 1
    assert safe_limit(None) == 25  # default
    assert safe_limit("abc") == 25
