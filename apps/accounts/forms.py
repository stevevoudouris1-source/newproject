"""Forms for the user-management UI.

Mass-assignment safety (CLAUDE.md → Security): this form deliberately does NOT
expose `role`, `is_staff`, `is_superuser`, or `is_claude_service`. Privilege is
granted only through the two permission checkboxes below, which create/remove
`Permission` rows via the permissions layer — never by flipping a model flag.
"""

from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.accounts.models import Permission, User
from apps.accounts.permissions import MANAGE_USERS, VIEW_USERS

_INPUT_CLASS = (
    "mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm "
    "shadow-sm focus:border-slate-500 focus:outline-none"
)


def _has_global_grant(user: User, name: str) -> bool:
    return user.permissions.filter(
        name=name, resource_type__isnull=True, resource_id__isnull=True
    ).exists()


class UserForm(forms.ModelForm):
    """Create or edit a user account and its user-management permissions."""

    can_view_users = forms.BooleanField(
        required=False,
        label="Can view users",
        help_text="Read-only access to the user list and detail pages.",
    )
    can_manage_users = forms.BooleanField(
        required=False,
        label="Can manage users",
        help_text="Create and edit users and grant permissions. Implies view.",
    )
    password1 = forms.CharField(
        required=False,
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Leave blank to keep the current password. New users can't sign in until one is set.",
    )
    password2 = forms.CharField(
        required=False,
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    field_order = [
        "username",
        "email",
        "first_name",
        "last_name",
        "password1",
        "password2",
        "is_active",
        "can_view_users",
        "can_manage_users",
    ]

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            field.widget.attrs.setdefault("class", _INPUT_CLASS)
        # Pre-tick the permission boxes from the existing grants when editing.
        if self.instance and self.instance.pk:
            self.fields["can_view_users"].initial = _has_global_grant(self.instance, VIEW_USERS)
            self.fields["can_manage_users"].initial = _has_global_grant(self.instance, MANAGE_USERS)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "The two password fields didn't match.")
            else:
                # Validate against AUTH_PASSWORD_VALIDATORS (length, common, etc.).
                try:
                    validate_password(p1, self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        elif not user.pk and not user.has_usable_password():
            # Brand-new user with no password set yet -> can't sign in until one is.
            user.set_unusable_password()
        if commit:
            user.save()
            self.sync_permissions(user)
        return user

    def sync_permissions(self, user: User) -> None:
        """Reconcile the two global grants with the checkbox state. Managing
        users implies viewing them, so a checked 'manage' box also grants view."""
        manage = self.cleaned_data["can_manage_users"]
        view = self.cleaned_data["can_view_users"] or manage
        self._set_grant(user, VIEW_USERS, view)
        self._set_grant(user, MANAGE_USERS, manage)

    @staticmethod
    def _set_grant(user: User, name: str, granted: bool) -> None:
        qs = Permission.objects.filter(
            user=user, name=name, resource_type__isnull=True, resource_id__isnull=True
        )
        if granted:
            Permission.objects.get_or_create(
                user=user, name=name, resource_type=None, resource_id=None
            )
        else:
            qs.delete()
