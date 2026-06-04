---
name: add-model
description: Step-by-step playbook for adding a new domain model to the Turn 5 Django starter app. Use whenever the user asks to "add a model," "track a new kind of record," "create a [thing] table," or anything that implies a new database-backed resource.
---

# Skill: add a new model

Adding a new model is the most common feature work in this codebase. The order below ensures you ship a model that is authorized (deny-by-default), scoped, paginated, indexed, and tested — without skipping a step.

All commands go through `uv`. The deny-by-default authorization lives ONLY in `apps.accounts.permissions`; never compare `user.role` anywhere else.

## Sequence

### 1. Confirm the shape with the user
- Resource name (singular, snake_case): `invoice`, `customer`, `widget`.
- Which app does it belong in (`apps/<app>/models.py`)?
- Fields: name, type, required (`null=False`), default, indexed?
- Relationships: `ForeignKey`, `ManyToManyField`? What `related_name`?
- Who can see/edit it? (admins always; which members; which permission name?)
- Sensitive data? Note it for the audit/history work (django-simple-history is Phase 3).

### 2. Write the model — `apps/<app>/models.py`
Give it a `ForUserQuerySet`-based manager so list views can call `.for_user()`. Admins see all; members see nothing by default — override `for_user` in your subclass to grant member visibility.

```python
from django.conf import settings
from django.db import models

from apps.common.scoping import ForUserQuerySet


class InvoiceQuerySet(ForUserQuerySet):
    def for_user(self, user):
        # admins see everything (base behavior); give members their own rows
        if user.role == user.ROLE_ADMIN:
            return self
        return self.filter(owner=user)


class Invoice(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_SENT, "Sent")]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    amount_cents = models.BigIntegerField()
    due_on = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = InvoiceQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["status", "due_on"])]

    def __str__(self):
        return f"Invoice #{self.pk} ({self.get_status_display()})"
```

- `null=False` (the default) on every required field — DB constraints AND model validation, belt-and-suspenders.
- Always set an explicit `related_name` on every `ForeignKey`.
- Add `Meta.indexes` for any field you filter or sort by.
- `role` comparison here is the ONE allowed exception **inside the queryset's `for_user`** — it mirrors how `ForUserQuerySet` itself works. Do not compare roles in views.

### 3. Make the migration — and review it
```bash
uv run python manage.py makemigrations
```
Open the generated file under `apps/<app>/migrations/` and read it. Confirm FK `on_delete`, indexes, `null`/`default`, and that it does only what you intended.

### 4. Migration safety check
```bash
uv run python manage.py lintmigrations
```
This is django-migration-linter. If it flags an unsafe operation (e.g. adding a `NOT NULL` column without a default to a populated table), follow the suggested safe pattern (add nullable → backfill → enforce in a later migration).

### 5. Register in the admin — `apps/<app>/admin.py`
```python
from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "amount_cents", "status", "due_on")
    list_filter = ("status",)
    search_fields = ("owner__email",)
```

### 6. Define the permission — `apps/accounts/permissions.py`
This is the ONLY place authorization logic lives. Register a permission name in the catalog and reference it everywhere else.

```python
# In apps/accounts/permissions.py
MANAGE_INVOICES = "manage_invoices"
PermissionsCatalog.register(MANAGE_INVOICES, "Create, edit, and delete invoices")
```

Views then call the module-level `authorize(user, name, resource=None)` (raises `PermissionDenied` → 403) or the non-raising `can(user, name, resource=None)`. Admins always pass; everyone else needs a matching `Permission` row (global grant for a global check, per-object grant for a scoped `resource`). No new function needed — `authorize`/`can` already drive off the registered name.

### 7. Add a factory / fixture
Prefer a factory for tests. Reference the custom user (`apps.accounts.models.User`) for FKs.

```python
# apps/<app>/tests/factories.py
import factory

from apps.accounts.tests.factories import UserFactory
from apps.invoices.models import Invoice


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    owner = factory.SubFactory(UserFactory)
    amount_cents = 10_000
    due_on = factory.Faker("future_date")
```

### 8. Write the tests (pytest + pytest-django) — before the view
Three required angles: **auth** (login enforced), **authz** (permission enforced), **happy path**.

```python
# apps/<app>/tests/test_invoices.py
import pytest
from django.urls import reverse

from apps.accounts.models import User, Permission
from apps.accounts.permissions import MANAGE_INVOICES

pytestmark = pytest.mark.django_db


def test_index_requires_login(client):
    resp = client.get(reverse("invoices:index"))
    assert resp.status_code == 302  # @login_required -> redirect to login


def test_index_denied_without_permission(client):
    member = User.objects.create_user(username="m@turn5.local", password="x")
    client.force_login(member)
    resp = client.get(reverse("invoices:index"))
    assert resp.status_code == 403  # deny by default


def test_index_happy_path_for_admin(client):
    admin = User.objects.create_user(
        username="a@turn5.local", password="x", role=User.ROLE_ADMIN
    )
    client.force_login(admin)
    resp = client.get(reverse("invoices:index"))
    assert resp.status_code == 200
```

Run:
```bash
uv run pytest apps/<app>
```

### 9. Add the URL — `apps/<app>/urls.py`
```python
from django.urls import path

from . import views

app_name = "invoices"
urlpatterns = [
    path("", views.index, name="index"),
]
```
Wire it into the project's root `urls.py` with `include("apps.invoices.urls")`.

### 10. Write the view — `apps/<app>/views.py`
Every view is `@login_required` by default. Mutating/scoped views call `authorize(...)` at the top. List views MUST use `Model.objects.for_user(request.user)` (never `.all()` / `.get(pk=...)`) and MUST paginate.

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.permissions import authorize, MANAGE_INVOICES
from apps.common.pagination import paginate
from .models import Invoice


@login_required
def index(request):
    authorize(request.user, MANAGE_INVOICES)  # raises 403 unless allowed
    invoices = Invoice.objects.for_user(request.user)  # row scoping, never .all()
    page = paginate(invoices, request)  # default page size = 25
    return render(request, "invoices/index.html", {"page": page})
```

For per-object views, fetch through the scoped manager and pass the object as the `resource`:
```python
invoice = Invoice.objects.for_user(request.user).get(pk=pk)
authorize(request.user, MANAGE_INVOICES, resource=invoice)
```

### 11. Write the template — `templates/invoices/index.html`
Extend `base.html`, render the page, and paginate.

```html
{% extends "base.html" %}
{% block content %}
  <ul>
    {% for invoice in page %}
      <li>#{{ invoice.id }} — {{ invoice.get_status_display }}</li>
    {% endfor %}
  </ul>

  {% if page.has_previous %}<a href="?page={{ page.previous_page_number }}">Prev</a>{% endif %}
  {% if page.has_next %}<a href="?page={{ page.next_page_number }}">Next</a>{% endif %}
{% endblock %}
```
If a `?limit` is user-controlled, clamp it with `safe_limit(request.GET.get("limit"))` before paginating. Tailwind classes work directly (django-tailwind-cli, no Node).

## Anti-patterns to avoid

- `Invoice.objects.all()` or `Invoice.objects.get(pk=...)` in a view — that's an IDOR. Always go through `.for_user(request.user)`.
- A view without an `authorize(...)` call on the mutating/scoped path — deny-by-default means you must explicitly allow.
- Comparing `user.role` anywhere outside `apps.accounts.permissions` (or a queryset's `for_user`).
- An `index` view that doesn't `paginate(...)`.
- A `ForeignKey` with no explicit `related_name`.
- Model validations but no DB-level `null=False` / index (race conditions exist).
- A migration committed without running `lintmigrations`.

## When to deviate

If the resource is admin-only with no member visibility, leave `for_user` at the base `ForUserQuerySet` behavior (members see nothing) and gate the view on a permission like `VIEW_ADMIN_DASHBOARD`. For a global-only capability, register a global grant; for per-object access, pass `resource=` to `authorize`.

## Definition of Done

Run the full check before committing:
```bash
uv run pytest
uv run ruff check .
uv run mypy .
bin/ci
```
Everything green = done. See the project's Definition-of-Done checklist (and `bin/ci`) for the authoritative gate.
