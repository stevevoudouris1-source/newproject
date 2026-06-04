"""Row-level scoping — the Django analog of Rails/Pundit `policy_scope`.

Every list view must fetch through `Model.objects.for_user(request.user)` rather
than `Model.objects.all()` (deny-by-default; CLAUDE.md → Authorization). Give
your model a manager built from `ForUserQuerySet` and override `for_user` with
the visibility rule for members; admins see everything by default.

Example:

    from django.db import models
    from apps.common.scoping import ForUserQuerySet

    class WidgetQuerySet(ForUserQuerySet):
        def for_user(self, user):
            if getattr(user, "role", None) == "admin":
                return self               # admins see everything
            return self.filter(owner=user)  # members see only their own

    class Widget(models.Model):
        owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE,
                                  related_name="widgets")
        objects = WidgetQuerySet.as_manager()
"""

from __future__ import annotations

from django.db import models


class ForUserQuerySet(models.QuerySet):
    def for_user(self, user):
        """Deny-by-default scope.

        Returns the full queryset for admins; returns an empty queryset for
        everyone else UNLESS a subclass overrides this with member visibility.
        Subclasses typically call `super().for_user(user)` first and, when it
        returns the empty queryset, apply their own filter.
        """
        if not getattr(user, "is_authenticated", False):
            return self.none()
        if getattr(user, "role", None) == "admin":
            return self
        return self.none()
