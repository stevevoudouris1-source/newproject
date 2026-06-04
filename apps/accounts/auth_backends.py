"""Authentication backends.

Three paths:
  - EntraOIDCBackend     — Microsoft Entra (Azure AD) SSO for humans. Only
                           registered when OIDC is configured (see settings).
  - ClaudeServiceBackend — password login restricted to the Claude service
                           account (is_claude_service=True). Always registered.
  - PasswordLoginBackend — username/password login for ordinary users, gated on
                           settings.PASSWORD_LOGIN_ENABLED. Lets a team run
                           standalone auth before — or instead of — Entra SSO.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


def generate_username(email: str) -> str:
    """OIDC_USERNAME_ALGO hook: use the email as the username verbatim."""
    return email


class EntraOIDCBackend(OIDCAuthenticationBackend):
    """Match/create users by their Entra email claim."""

    def _email(self, claims) -> str:
        return (claims.get("email") or claims.get("preferred_username") or "").strip()

    def filter_users_by_claims(self, claims):
        email = self._email(claims)
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(username__iexact=email)

    def create_user(self, claims):
        email = self._email(claims)
        return self.UserModel.objects.create(
            username=email,
            email=email,
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
            role=self.UserModel.ROLE_MEMBER,
        )

    def update_user(self, user, claims):
        user.email = self._email(claims) or user.email
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save(update_fields=["email", "first_name", "last_name"])
        return user


class ClaudeServiceBackend(ModelBackend):
    """Authenticate ONLY the Claude service account via password.

    Humans must use Entra SSO. This backend refuses any user that is not
    flagged `is_claude_service`, so a normal user's password is never accepted
    here even if one were set.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            # Run the hasher once to avoid leaking user existence via timing.
            UserModel().set_password(password)
            return None
        if not getattr(user, "is_claude_service", False):
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class PasswordLoginBackend(ModelBackend):
    """Username/password login for ordinary (non-service) users.

    Available only while ``settings.PASSWORD_LOGIN_ENABLED`` is true, so a team
    can use standalone password auth before Entra SSO is configured (or instead
    of it), and turn it off later to force SSO-only. The Claude service account
    is intentionally excluded here — it authenticates via ClaudeServiceBackend
    regardless of this flag.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not getattr(settings, "PASSWORD_LOGIN_ENABLED", True):
            return None
        # ModelBackend handles the lookup, password check, is_active gate, and a
        # constant-time dummy hash for unknown users (no timing oracle).
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is None or getattr(user, "is_claude_service", False):
            return None
        return user
