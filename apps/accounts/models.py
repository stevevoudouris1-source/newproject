from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models

from apps.common.scoping import ForUserQuerySet


class UserQuerySet(ForUserQuerySet):
    def for_user(self, user):
        """Deny-by-default row scoping for user records.

        Anyone permitted to view or manage users sees every account (admins
        included, since `can()` short-circuits for them); everyone else sees
        none. Imported lazily to avoid an import cycle with the permissions
        module at app-load time.
        """
        from apps.accounts.permissions import MANAGE_USERS, VIEW_USERS

        if not getattr(user, "is_authenticated", False):
            return self.none()
        if user.can(VIEW_USERS) or user.can(MANAGE_USERS):
            return self
        return self.none()


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):  # type: ignore[misc]
    """Django's UserManager (create_user/create_superuser, used in migrations)
    plus the `for_user` row-scoping helper from UserQuerySet."""


class User(AbstractUser):
    """Application user.

    `role` is the coarse layer (member/admin); `Permission` rows are the
    fine-grained layer. Authorization is deny-by-default: check access through
    `user.can(...)` / `apps.accounts.permissions.authorize(...)`, never by
    comparing `role` outside of `apps.accounts.permissions`.
    """

    ROLE_MEMBER = "member"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [(ROLE_MEMBER, "Member"), (ROLE_ADMIN, "Admin")]

    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    is_claude_service = models.BooleanField(
        default=False,
        help_text="True only for the Claude admin service account.",
    )

    objects = UserManager()  # type: ignore[misc]

    def can(self, permission_name: str, resource=None) -> bool:
        """Return True if this user may perform `permission_name`.

        Admins can do anything. Otherwise the user must hold a matching
        `Permission` row — either global (no resource) or scoped to the exact
        resource instance passed in.
        """
        if self.role == self.ROLE_ADMIN:
            return True
        qs = self.permissions.filter(name=permission_name)
        if resource is not None:
            qs = qs.filter(
                resource_type=resource.__class__.__name__,
                resource_id=resource.pk,
            )
        else:
            qs = qs.filter(resource_type__isnull=True, resource_id__isnull=True)
        return qs.exists()


class Permission(models.Model):
    """A fine-grained grant for one user.

    A row with null resource_type/resource_id is a *global* grant of `name`;
    a row with both set is a per-object grant scoped to that instance.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="permissions")
    name = models.CharField(max_length=64)
    # NULL (not "") is meaningful here: it marks a *global* grant and is what
    # can() filters on via resource_type__isnull. Hence DJ001 is intentional.
    resource_type = models.CharField(max_length=64, blank=True, null=True)  # noqa: DJ001
    resource_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name", "resource_type", "resource_id"],
                name="permissions_unique_per_user_resource",
            )
        ]
        indexes = [models.Index(fields=["resource_type", "resource_id"])]

    def __str__(self) -> str:
        scope = f"{self.resource_type}#{self.resource_id}" if self.resource_type else "global"
        return f"{self.user} :: {self.name} ({scope})"
