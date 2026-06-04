"""Authorization — deny-by-default.

This module is the ONLY place allowed to reason about roles directly. Views and
templates ask `can(user, name, resource)` or call `authorize(...)`; they never
check `user.role == "admin"` themselves.

Analogous to the Rails template's Pundit policies + permission catalog.
See .claude/skills/add-permission.md to add a new permission name.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied


class PermissionsCatalog:
    """Canonical registry of fine-grained permission names.

    Register every permission here so there is a single source of truth that
    the admin UI, policies, and views all reference by constant.
    """

    REGISTRY: dict[str, str] = {}

    @classmethod
    def register(cls, name: str, description: str) -> str:
        cls.REGISTRY[name] = description
        return name

    @classmethod
    def all(cls) -> dict[str, str]:
        return dict(cls.REGISTRY)

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(name, f"{name} — {desc}") for name, desc in cls.REGISTRY.items()]


# Baseline permissions shipped with the template. Add your own next to these.
VIEW_USERS = PermissionsCatalog.register("view_users", "View user accounts (read-only)")
MANAGE_USERS = PermissionsCatalog.register(
    "manage_users", "Create/edit users and grant or revoke permissions"
)
VIEW_ADMIN_DASHBOARD = PermissionsCatalog.register(
    "view_admin_dashboard", "View the internal admin dashboard"
)


def can(user, permission_name: str, resource=None) -> bool:
    """Non-raising check. Returns True only for an authenticated, permitted user."""
    return bool(getattr(user, "is_authenticated", False) and user.can(permission_name, resource))


def authorize(user, permission_name: str, resource=None) -> bool:
    """Deny-by-default gate. Raises PermissionDenied (HTTP 403) unless allowed.

    Call this at the top of every view that mutates or exposes scoped data.
    """
    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    if not user.can(permission_name, resource):
        raise PermissionDenied(f"Not permitted: {permission_name}")
    return True
