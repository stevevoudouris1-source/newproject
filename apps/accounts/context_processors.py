"""Template context processors.

`nav_capabilities` exposes a couple of booleans so shared chrome (the nav bar)
can show or hide links without reaching into `user.role` — authorization stays
in `apps.accounts.permissions`.
"""

from __future__ import annotations

from apps.accounts.permissions import MANAGE_USERS, VIEW_USERS, can


def nav_capabilities(request):
    user = getattr(request, "user", None)
    can_manage_users = can(user, MANAGE_USERS)
    return {
        # Managing users implies viewing them.
        "nav_can_view_users": can(user, VIEW_USERS) or can_manage_users,
        "nav_can_manage_users": can_manage_users,
    }
