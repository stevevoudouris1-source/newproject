# Definition of Done

Claude must verify every item on this checklist before reporting a task complete. If any item fails, the task is **not done** — fix it and re-check. If you must skip an item, say so out loud and explain why.

**Match effort to the change — don't over-test.** This checklist is for *substantial* changes (new behavior, logic, schema, views, user-facing flows). **Minor tweaks — copy/text, styling, spacing, colours, comments, docs, small config — need no new tests and no full test run;** confirm the page still loads, then save.

## Functional

- [ ] The user's request is implemented and behaves as described.
- [ ] If anything was unclear, the user was asked rather than guessed.
- [ ] All affected pages still load without errors.

## Tests

- [ ] For behavioral/logic changes, a failing test was written **before** the change (TDD). *(Minor tweaks: skip.)*
- [ ] `uv run pytest` passes (for changes that touch behavior; minor tweaks need no run).
- [ ] Browser tests pass: `uv run pytest -m browser` (needs `uv run playwright install chromium` once).
- [ ] Any new view has a test covering: unauthenticated → redirect to login, unauthorized → 403 (`PermissionDenied`), authorized → expected behavior.
- [ ] Any new permission registered in `apps.accounts.permissions` has a test for every relevant role (member vs admin) and for global vs per-object grants.
- [ ] Any new user-visible flow has a Playwright happy-path test.

## Code quality

- [ ] `uv run ruff check .` is clean.
- [ ] `uv run ruff format --check .` is clean (run `uv run ruff format` to fix).
- [ ] `uv run mypy .` is clean (when type checking is enabled).
- [ ] No `breakpoint()`, `pdb.set_trace()`, or stray `print()` left in production code.
- [ ] No commented-out code blocks left behind.
- [ ] New functions are short and named for what they do.

## Security & authorization

- [ ] Every new view has `@login_required` (it is the default — only opt out with an explicit, justified comment).
- [ ] Every mutating or scoped view calls `authorize(user, name, resource=None)` from `apps.accounts.permissions` (deny by default — a missing call means no access).
- [ ] No `user.role` comparison anywhere outside `apps.accounts.permissions`. Use `can()` / `authorize()` instead.
- [ ] Every view that takes an id loads via `Model.objects.for_user(request.user)`, **never** `Model.objects.get(pk=...)` or `Model.objects.all()`.
- [ ] No new sensitive form field lets a non-admin set `role`, `is_claude_service`, or anything in `Permission`.
- [ ] No real secrets in source. New config keys go in `.env.example` (keys only); actual values stay in the gitignored `.env`. No `.env*` (besides `.env.example`) committed.

## Database & migrations

- [ ] `uv run python manage.py lintmigrations` is clean (if it warned, the warning was addressed, not bypassed without justification).
- [ ] Every new data-bearing field is `null=False` — and has a `default=` if the table already has rows.
- [ ] Every `ForeignKey` has an explicit `related_name`.
- [ ] Every column referenced in a filter or ordering is indexed (`db_index=True` or a `Meta.indexes` entry); every FK is indexed.
- [ ] No data backfills inside a schema migration — use a separate data migration or a `manage.py` command.
- [ ] Any schema change has a test.

## Performance

- [ ] Every list view paginates with `paginate(queryset, request, default=25)` from `apps.common.pagination`.
- [ ] User-supplied `?limit` is clamped via `safe_limit(requested, default=25, maximum=100)`.
- [ ] N+1 queries are avoided via `select_related` / `prefetch_related`. (`nplusone` will flag misses in tests.)

## Communication

- [ ] You told the user, in plain English, what changed and any caveats they should know about.
- [ ] If you skipped any item above, you explained why.
- [ ] If you noticed something unrelated that's broken or could be improved, you mentioned it but did **not** fix it without permission.
