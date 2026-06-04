---
name: write-migration
description: Conventions and safety rules for writing Django migrations in the Turn 5 starter. Use whenever you are creating, editing, or running a migration — especially any migration that touches an existing table with data.
---

# Skill: write a safe migration

Migrations are the most common way Claude can break a production app. `django-migration-linter` blocks the worst patterns automatically (`uv run python manage.py lintmigrations`), but it only catches what it knows about — follow this skill so your migrations pass the first time and stay safe.

Remember the two databases: **prototype mode** runs SQLite (`db/development.sqlite3`); **real mode** runs SQL Server via `DATABASE_URL`. SQLite forgives almost everything; SQL Server does not. Write every migration as if it will run against a populated SQL Server table, because in production it will.

## Always

- **Add new columns nullable-first (`null=True`).** Never add a `NOT NULL` column to a populated table in one step. Use the three-step pattern below.
- **Index every ForeignKey.** Django adds an index automatically when you use `models.ForeignKey(...)`, so prefer that. If you ever add a raw index column by hand, also add the index explicitly (`models.Index(...)` in `Meta.indexes` or `db_index=True`).
- **Index any column you filter or sort by.** `Model.objects.filter(status="open")` needs `db_index=True` on `status` once the table grows past a few thousand rows.
- **One concern per migration, deployable independently.** Phase 1: add the nullable column. Phase 2 (separate command run): backfill. Phase 3: tighten to `null=False`. Don't combine.
- **Run `uv run python manage.py makemigrations --check --dry-run`** before committing. It exits non-zero if your models and migrations are out of sync — i.e. you changed a model but forgot to generate the migration. `bin/ci` runs this; don't let it surprise you.

## Never

- **Never put data changes inside a schema migration.** No backfills, no `update()`, no row writes in a `migrations.RunPython` that touches business data. Schema migrations must be fast and atomic. Write a **separate management command** instead (see below). (The one sanctioned exception is the existing idempotent service-account provisioning in `apps/accounts/migrations/0002_provision_claude_admin.py` — follow its pattern only for similar idempotent bootstrap data, never for backfilling user data.)
- **Never add a `NOT NULL` column without a default to a populated table.** The linter rejects this. Existing rows have no value and the constraint fails.
- **Never drop a column that code still references.** Search first: `Grep` for the field name across `apps/`. The linter flags `DROP COLUMN` because rolling code that still selects the column will 500.
- **Never change a column's type in place.** Add a new column, backfill via command, switch reads, drop the old. Spans multiple deploys.
- **Never compare `user.role` in a migration** (or anywhere outside `apps.accounts.permissions`). If a data migration needs an authorization-shaped decision, that's a smell — reconsider.

## The three-step pattern: adding a required column to a populated table

This is the single most important pattern. Three migrations, two of them schema-only, with a backfill command in between.

### Step 1 — add the column nullable, with a default for new rows

```python
# apps/<app>/migrations/00XX_add_status_to_invoice.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("<app>", "00XX_previous")]
    operations = [
        migrations.AddField(
            model_name="invoice",
            name="status",
            field=models.CharField(max_length=20, null=True, default="open", db_index=True),
        ),
    ]
```

New rows now get `"open"`. Existing rows are `NULL` — that's fine, we fix them next.

### Step 2 — backfill in a SEPARATE management command (NOT a migration)

```python
# apps/<app>/management/commands/backfill_invoice_status.py
from django.core.management.base import BaseCommand
from apps.invoices.models import Invoice

class Command(BaseCommand):
    help = "Backfill Invoice.status for rows created before the column existed."

    def handle(self, *args, **options):
        qs = Invoice.objects.filter(status__isnull=True)
        updated = qs.update(status="open")  # set-based; one UPDATE
        self.stdout.write(self.style.SUCCESS(f"Backfilled {updated} rows"))
```

Run it: `uv run python manage.py backfill_invoice_status`. It's idempotent (filters on `status__isnull=True`), so re-running is safe. For very large tables, iterate in batches instead of one `update()`.

### Step 3 — tighten to NOT NULL once every row has a value

```python
migrations.AlterField(
    model_name="invoice",
    name="status",
    field=models.CharField(max_length=20, null=False, default="open", db_index=True),
)
```

Keep the `default` so the constraint is satisfiable and future inserts are safe. Update the model field to `null=False` and re-run `makemigrations` to generate this; never hand-edit the field state out of sync with the model.

## What `django-migration-linter` rejects, and why

Run it explicitly with `uv run python manage.py lintmigrations` (also wired into `bin/ci` and the lefthook pre-commit hooks). Common rejections:

- **Adding `NOT NULL` without a default on a populated table** — existing rows can't satisfy the constraint; the migration fails mid-deploy. Fix: the three-step pattern above.
- **Dropping a column** — old application code (during a rolling deploy, or a rollback) still selects it and 500s. Fix: stop referencing it in code and deploy that first; drop the column in a later, separate migration.
- **Renaming a column** — same rolling-deploy hazard. Fix: add new column, dual-write, backfill via command, switch reads, drop old.
- **Changing a column type** — can rewrite the whole table and lose data. Fix: add-new / backfill / drop-old.

When the linter complains, **read the message** — it names the safe pattern. Only suppress a warning after you've verified it's a genuine false positive for this specific case, and leave a comment explaining why.

## Keeping migrations in sync

- `uv run python manage.py makemigrations --check --dry-run` — fails if a model change has no migration. Run before every commit.
- `uv run python manage.py makemigrations` — generate the migration after a model change. **Always review the generated file** before committing; auto-generated `AlterField` operations are where unsafe `NOT NULL` changes sneak in.
- Never edit a migration that's already been applied in production. Add a new one.

## SQLite vs SQL Server gotchas

You develop on SQLite (prototype mode) but deploy on SQL Server (real mode). Things that "work locally" can break in prod:

- **SQLite rebuilds the table for most `ALTER`s**, silently tolerating operations SQL Server rejects (e.g. adding a `NOT NULL` column without a usable default). A migration that's green on SQLite can still fail on SQL Server. Trust the linter, not your local run.
- **String length matters on SQL Server.** Always set `max_length` on `CharField`. SQLite ignores it; SQL Server enforces it and indexing very long columns can fail.
- **Case sensitivity / collation differ.** Don't rely on SQLite's loose, case-insensitive text comparisons; SQL Server collation may behave differently. Don't bake comparison assumptions into data migrations.
- **Defaults and `NOT NULL` are strictly enforced on SQL Server.** This is exactly why the nullable-first → backfill → tighten sequence exists.
- **The `warehouse` alias is read-only.** Never generate or run migrations against `WAREHOUSE_DATABASE_URL`. Migrations target the default database only.

## Reviewing your own migration

Before committing, ask:

1. Does this add a `NOT NULL` column to a table that already has rows? (If yes, you need the three-step pattern.)
2. Is there any data change living inside a schema migration? (If yes, move it to a management command.)
3. Does every new ForeignKey and every filtered/sorted column have an index?
4. Did `makemigrations --check --dry-run` and `lintmigrations` both pass?
5. Is it reversible — or, if I deploy and immediately roll back, will old code still run against this schema?

If any answer is "I'm not sure," ask the user before deploying.
