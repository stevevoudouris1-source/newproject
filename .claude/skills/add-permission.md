---
name: add-permission
description: How to add a new fine-grained permission (named capability) and enforce it in views, templates, and tests. Use when a user needs a specific capability (e.g. edit invoices) without being made a full admin.
---

# Skill: add a new permission

The template has two layers of authorization:

1. **Role** (`User.role`, `member` or `admin`). Coarse-grained.
2. **Permissions** (the `Permission` model + the `apps.accounts.permissions` catalog). Fine-grained, named capabilities like `manage_invoices` or `view_payroll`.

Use a permission when "admin / non-admin" is too coarse — e.g. a finance user who can edit invoices but isn't an admin.

**DENY BY DEFAULT.** No grant = no access. Admins are implicitly allowed everything.

**THE RULE:** all authorization lives in `apps.accounts.permissions`. Never compare `user.role` (or call `user.is_admin`) anywhere else — not in views, not in templates, not in querysets. Views call `authorize(...)` / `can(...)`; querysets call `.for_user(user)`.

---

## 1. Register the permission

Add it to the catalog in `apps/accounts/permissions.py`, right next to the baseline constants `MANAGE_USERS` and `VIEW_ADMIN_DASHBOARD`. Use a snake_case, action-oriented name.

```python
# apps/accounts/permissions.py

MANAGE_USERS = "manage_users"
VIEW_ADMIN_DASHBOARD = "view_admin_dashboard"
MANAGE_INVOICES = "manage_invoices"        # <-- new

PermissionsCatalog.register(MANAGE_USERS, "Create, edit, and deactivate user accounts")
PermissionsCatalog.register(VIEW_ADMIN_DASHBOARD, "View the admin dashboard")
PermissionsCatalog.register(MANAGE_INVOICES, "Create and edit invoices")  # <-- new
```

`register()` records it in `REGISTRY`. `PermissionsCatalog.all()` lists every registered permission; `PermissionsCatalog.choices()` gives `(name, description)` pairs for forms/dropdowns. Registering here is what makes the permission selectable in the admin UI instead of a free-text field.

---

## 2. Grant it (create `Permission` rows)

A registered permission grants nothing on its own — you must create `Permission` rows for the users who should have it.

**Global grant** (the user has the capability everywhere): leave `resource_type` and `resource_id` null.

```python
from apps.accounts.models import Permission
from apps.accounts.permissions import MANAGE_INVOICES

Permission.objects.create(user=user, name=MANAGE_INVOICES)
```

**Per-object grant** (only for one specific record): set both `resource_type` and `resource_id`.

```python
Permission.objects.create(
    user=user,
    name=MANAGE_INVOICES,
    resource_type="invoice",
    resource_id=str(invoice.pk),
)
```

Notes:
- A `UniqueConstraint` on `(user, name, resource_type, resource_id)` prevents duplicate grants — use `get_or_create` if a row may already exist.
- A global check (`resource=None`) requires a **global** grant; a per-object grant alone will not satisfy it.
- Day-to-day, admins grant permissions through the **admin UI** (Django admin / the manage-users views). For seeding fixed grants, write a **data migration** so the grant ships with the code.

---

## 3. Check it in views

Enforce permissions at the top of every mutating or resource-scoped view. Every view is already `@login_required` by default, so you're only checking the capability.

```python
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import authorize, MANAGE_INVOICES

def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice.objects.for_user(request.user), pk=pk)
    authorize(request.user, MANAGE_INVOICES, resource=invoice)  # raises 403 if denied
    ...
```

- `authorize(user, name, resource=None)` raises Django's `PermissionDenied` (HTTP 403) unless allowed. Use it to **gate an action**.
- `can(user, name, resource=None)` returns a `bool` and never raises. Use it for **branching** (show/hide, choose behaviour).

```python
from apps.accounts.permissions import can, MANAGE_INVOICES

context["can_edit"] = can(request.user, MANAGE_INVOICES, resource=invoice)
```

Always fetch rows through `.for_user(request.user)` (never `.all()` / bare `.get(pk=...)`), and paginate list views with `paginate(queryset, request)`. Row scoping and permission checks are complementary: scoping limits *which rows*, `authorize` gates *which actions*.

---

## 4. Check it in templates

Pass a boolean from the view (via `can(...)`) into the context and branch on it — do **not** reach into `user.role` in the template.

```django
{% if can_edit %}
  <a href="{% url 'invoice_update' invoice.pk %}"
     class="text-sky-600">Edit</a>
{% endif %}
```

---

## 5. Test allowed + denied

Always assert both the allowed and the denied path. Denied is the more important test — it proves deny-by-default still holds.

```python
import pytest
from django.core.exceptions import PermissionDenied
from apps.accounts.models import User, Permission
from apps.accounts.permissions import authorize, can, MANAGE_INVOICES

@pytest.mark.django_db
def test_member_with_grant_is_allowed():
    user = User.objects.create_user(username="fin", role=User.ROLE_MEMBER)
    Permission.objects.create(user=user, name=MANAGE_INVOICES)
    assert can(user, MANAGE_INVOICES) is True
    authorize(user, MANAGE_INVOICES)  # does not raise

@pytest.mark.django_db
def test_member_without_grant_is_denied():
    user = User.objects.create_user(username="nobody", role=User.ROLE_MEMBER)
    assert can(user, MANAGE_INVOICES) is False
    with pytest.raises(PermissionDenied):
        authorize(user, MANAGE_INVOICES)

@pytest.mark.django_db
def test_per_object_grant_does_not_leak_globally():
    user = User.objects.create_user(username="scoped", role=User.ROLE_MEMBER)
    Permission.objects.create(
        user=user, name=MANAGE_INVOICES,
        resource_type="invoice", resource_id="1",
    )
    assert can(user, MANAGE_INVOICES) is False  # global check needs a global grant
```

Run them:

```sh
uv run pytest
```

---

## Gotchas

- **Admins are always allowed.** `user.can(...)`, `can(...)`, and `authorize(...)` all return True / pass for `role=admin`, regardless of `Permission` rows. If you need a capability admins should *not* have, that's a special case — handle it inside `apps.accounts.permissions`, never with a `user.role` check elsewhere.
- **Never check `user.role` outside `apps.accounts.permissions`.** Add a `can(...)` helper or a new permission instead. This keeps authorization in one auditable place and survives changes to the role choices.
- **Global vs per-object:** a global check (`resource=None`) needs a global grant; a per-object check needs `resource` passed *and* a matching per-object (or global) grant. Pass the resource whenever the capability is per-record.
- **Register before you grant.** Creating a `Permission` row for an unregistered name still works in the DB, but it won't appear in the admin dropdown and signals an undocumented capability — always `PermissionsCatalog.register(...)` first.
