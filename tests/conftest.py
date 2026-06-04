import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def claude_password():
    return "test-service-password-1234567890ABcd"


@pytest.fixture
def claude_user(db, claude_password):
    """The Claude service account with a known, usable password.

    The provisioning migration may already have created this row (with an
    unusable password in test/CI); this fixture makes it deterministic.
    """
    User = get_user_model()
    user, _ = User.objects.update_or_create(
        username="claude@turn5.local",
        defaults={
            "email": "claude@turn5.local",
            "role": User.ROLE_ADMIN,
            "is_claude_service": True,
            "is_staff": True,
            "is_superuser": False,
            "is_active": True,
        },
    )
    user.set_password(claude_password)
    user.save()
    return user


@pytest.fixture
def member_user(db):
    User = get_user_model()
    user = User.objects.create(
        username="member@turn5.local",
        email="member@turn5.local",
        role=User.ROLE_MEMBER,
    )
    user.set_password("member-password-1234567890ABcd")
    user.save()
    return user
