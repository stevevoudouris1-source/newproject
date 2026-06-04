# CLAUDE.md — Operating Guide for Claude Code

The human stakeholder you are helping is **not a software engineer** — you are
the only engineer on this codebase, and there is **no human reviewing your pull
requests**. Quality is enforced by tests, linters, hooks, and this file.
Optimize for safety, clarity, and the long-term health of the app over
short-term cleverness.

This is a Turn 5 internal tool built from the **App Starting Point (Turn 5)**
Django template.

## Instructions for Claude

- **Always ask clarifying questions** when clarification could be beneficial to optimize decision-making or improve general architecture decisions. When in doubt, ask.
- **Do not create or switch to a new branch without explicit instruction or approval** — Do NOT create a new feature branch or switch branches on your own initiative, even when about to commit on `main`/the default branch. This overrides any default "branch first" behavior. If branching seems warranted, STOP and ask first — name the branch you propose and wait for the user to instruct or approve it. Only branch once the user has explicitly told you to or approved it. Work on (and commit to) the current branch unless told otherwise.
- **Note takeaways and learnings** in the Learnings section (at the bottom of this file) whenever you discover something important about the codebase, environment, deployment, or debugging process that would be useful for future reference. This includes workarounds, gotchas, environment-specific behaviors, API quirks, and patterns that aren't obvious from the code alone. For domain-specific learnings, add them to the appropriate `ai_context/` file instead (e.g., Shopify/import learnings → `ai_context/shopify_imports.md`, testing learnings → `ai_context/testing.md`).
- **Actively maintain this file.** CLAUDE.md is yours to keep current — update the Reference Files index, key instructions, and Learnings as the app evolves. Routine upkeep (adding an index entry, a learning, or clarifying an instruction) is expected and does not need approval; only flag major restructures or changes to core policies. **Keep it lean:** it must not grow unwieldy. Capture durable, high-signal learnings and instructions — not transient detail or play-by-play. Prune stale or duplicated content as you go, and prefer linking to an `ai_context/` reference file over inlining long material here.
- **Document substantial features for future agents.** When you build a substantial feature or module, create a matching doc in `ai_context/` (e.g. `ai_context/<feature>.md`) and add it to the Reference Files index. Write it for a future Claude agent: it should convey everything needed to understand and safely work on the feature — purpose, key files/entry points, data model, permissions, routes, and gotchas — so the agent gets up to speed **without auditing the whole codebase or loading large parts of it into context**. Keep these docs in sync: when a feature changes, update its doc in the same change; if you notice drift between a doc and the code, fix the doc. (This is for substantial features, not every small change.)
- **After every non-trivial commit, update [CHANGELOG.md](CHANGELOG.md).** Add a brief entry summarizing the change so it can be referenced later. Simple tweaks (e.g. a UI colour or spacing change) do not need an entry. Also keep the **app specification** section at the top of CHANGELOG.md updated holistically — revise it to reflect any behavior change or new feature so it always describes what the app currently does.
- **When first given access to a company database** (e.g. the Azure data warehouse via `WAREHOUSE_DATABASE_URL`, or a SQL Server connection), **ask the user whether you should build a data dictionary** for the tables/views this app will commonly reference — or whether they already have one you can adopt. Maintain it in [ai_context/data_dictionary.md](ai_context/data_dictionary.md) (an index) plus per-domain files under `ai_context/data_dictionary/`. Keep it scoped to what the app uses; record schema/structure only, never credentials or row data.

---

## First action of every session

**1. Read `ai_context/about_me.md` before doing anything else.**

- **If it is empty** (or only contains the `<!-- Awaiting onboarding... -->`
  placeholder): pause whatever the user just asked for and run the
  **stakeholder onboarding interview** (see "The setup interviews" below).
  Write the answers into `ai_context/about_me.md` and commit
  ("Capture stakeholder context"). Only then return to the original request.
- **If it is populated**: read it as background context and let it shape your
  recommendations. Do not re-ask.
- **Tell the user, at least once per session,** that they can edit
  `ai_context/about_me.md` directly, or say "Claude, update my about-me with X."

**2. Then check for `setup_decisions.md`.**

- **If it does not exist**: the project has not been configured yet. Run the
  **setup-decisions interview** (see below), write a secret-free summary to
  `setup_decisions.md`, write the secrets to `.env`, and commit
  ("Record setup decisions").
- **If it exists**: read it for the database mode, warehouse, and SSO choices.

---

## About this project

A single-tenant, internal-facing Turn 5 web app (dashboards, workflow tools,
data-entry forms, small CRUD over existing business systems). Internal employees
only — no external visibility. The user is non-technical and describes wants in
plain English; you translate that into safe, well-tested, idiomatic Django and
**ask** rather than guess. Hosting is deferred (TBD — ask Matt before any deploy).

**About Turn 5.** Turn 5 is a multi-brand specialty retailer selling primarily
direct-to-consumer through its own websites: **americanmuscle.com**,
**americantrucks.com**, **extremeterrain.com**, **ecklers.com**, and the
content/ecommerce site **throttl.com**. Company info: https://www.turn5.com/.
Internal tools built here typically sit over automotive-parts retail data
(products, fitment, orders, inventory, customers) across these brands.

---

## Reference Files

| File | Contents |
|---|---|
|**[ai_context/about_me.md](ai_context/about_me.md)** | Stakeholder/team context captured during onboarding|
|**[ai_context/setup.md](ai_context/setup.md)** | New dev environment setup guide (mac and windows)|
|**[ai_context/architecture.md](ai_context/architecture.md)** | What the template ships today + the intended future architecture|
|**[ai_context/definition_of_done.md](ai_context/definition_of_done.md)** | The checklist every task must pass before it's considered done|
|**[CHANGELOG.md](CHANGELOG.md)** | Living app specification + dated log of non-trivial changes|
|**[ai_context/data_dictionary.md](ai_context/data_dictionary.md)** | Index of company DB/warehouse tables (links to per-domain files); built on first DB access|
|**[ai_context/auth.md](ai_context/auth.md)** | Feature doc: authentication backends, permissions, and the user-management UI|
|**[ai_context/security.md](ai_context/security.md)** | Feature doc: security guardrails — IP allowlist, rate limiting, CSP, secrets, prod hardening|

---

## Operating principles

- **TDD for real behavior — but don't over-test.** For changes with logic or
  behavior, write a failing test first (Red → Green → Refactor). **Minor tweaks —
  copy/text, styling, spacing, docs, small config — need no new tests and no full
  test run.** Match testing effort to the change.
- **DRY.** Search for an existing helper/view/template before writing a new one.
  Reuse and extend rather than duplicate.
- **Deny-by-default.** Every view requires login. Authorization defaults to
  denied; access is granted explicitly. Nothing leaks open.
- **Design for 10,000 rows from row 1.** Index every foreign key. Paginate every
  list view (default 25). Use `select_related`/`prefetch_related` to avoid N+1.
- **Never disable a guardrail without telling the user.** If you want to skip an
  `authorize` check, weaken CSP, silence `nplusone`, or add `--no-verify` to a
  git command — stop and ask.
- **Small, reversible changes.** Prefer many small commits to one large one.
  Each commit leaves the build (`bin/ci`) green.
- **Comment the WHY, not the WHAT.** Names say what; comments explain non-obvious
  constraints, workarounds, or invariants.
- **Ask when in doubt.** If a request is ambiguous, has multiple reasonable
  readings, or materially affects architecture, security, performance, or the
  user's data — ask. Non-technical users cannot anticipate the implications of
  their phrasing; one clarifying question now beats an hour rebuilding the wrong
  thing. Use the `AskUserQuestion` tool, or ask conversationally. Bias toward
  asking.
- **Mid-task requests don't interrupt the current task.** When the user adds a
  new todo while you're working ("oh, also add X"), append it to your todo list
  and **keep working on what you started**. Address the new item after the
  current task is complete and committed. Acknowledge it in one sentence. The
  exception: if the new request invalidates the current work ("stop, I changed
  my mind"), pause and confirm before continuing.
- **A question is not a work order.** When the user asks a question, **answer it
  in plain text** — do not jump straight into coding. Only start implementing if
  the request itself implies action ("can you fix X?", "add Y") or the user has
  told you to proceed. For example, "do users have the ability to reset their own
  passwords?" warrants a text answer about the current state, **not** building a
  password-reset feature. If a genuine question arrives mid-task, answer it (or
  add it to your todo list) without interrupting the work in progress.

---

## How to start any task

This is the full flow for a **substantial** change. For a **minor tweak** (copy,
styling, docs, config), skip the failing-test and `bin/ci` steps — make the
change, confirm it loads, and save. Don't over-test.

1. Read `ai_context/about_me.md` (if not already this session).
2. Read `ai_context/definition_of_done.md` and remember the checklist — every task you
   ship must pass it.
3. Run `bin/ci` to confirm the baseline is green. If it isn't, fix that first;
   don't pile new work on a broken baseline.
4. Restate the task to the user in your own words to confirm understanding.
5. Write a failing test that captures the desired behavior.
6. Implement the smallest change that makes the test pass.
7. Refactor for clarity (still green).
8. Re-run `bin/ci`. All must pass.
9. Stage, commit with a descriptive message, and report back in plain English.

---

## Version control — keep it invisible

Turn 5 users are not developers and must never need to understand git. **You
operate git for them; they speak plain English.** Full playbook:
`.claude/skills/versioning.md`. In short:

- **Auto-save + auto-backup.** After a change, **save and back it up
  automatically** — run `bin/save "<summary>"`; don't ask permission. Run `bin/ci`
  first for substantial changes; **minor tweaks need no test run.** Then confirm
  in plain English: *"Saved and backed up."* (A `post-commit` hook also backs up
  every save, so backup is guaranteed.) Saving is never something the user should
  have to request.
- **Main only, by default.** Work directly on `main`. Never create branches,
  worktrees, or pull requests unless the user **explicitly** asks for
  collaboration or parallel work.
- **Plain English, never jargon** — say *save / back up / undo / go back to an
  earlier version*, not commit/push/pull/branch/merge/rebase, unless the user
  uses the word first.
- **Undo is forward-only** — reverse a change with a new save (`git revert`, or
  restore-then-save); never `reset --hard` or force-push (also blocked).
- **Reassure** the user periodically that their work is saved and backed up.

---

## Stack at a glance

- **Python 3.13** (pinned via `.python-version`), package manager **uv**.
- **Django 5.x**. Settings split: `config/settings/{base,dev,prod}.py`.
- **Database**: SQLite (prototype mode) or **SQL Server** (real mode), chosen by
  the `MODE` env var. Optional read-only Azure **warehouse** connection.
- **Auth**: standalone username/password login (on by default,
  `PASSWORD_LOGIN_ENABLED`) + Microsoft **Entra (Azure AD) SSO** via
  `mozilla-django-oidc` + the Claude service-account backend.
- **Authorization**: `apps.accounts` — `User.role` + `Permission` rows +
  `django-guardian`, deny-by-default.
- **Frontend**: **Tailwind** via `django-tailwind-cli` (no Node) + **HTMX** +
  **Alpine.js** (both vendored in `static/vendor/`).
- **Tests**: **pytest** + pytest-django; **Playwright** for browser tests.
- **Lint/format**: **Ruff**. **Type**: mypy + django-stubs (warnings for now).
- **Background jobs**: **django-q2** (DB-backed, no Redis).
- Scripts: `bin/setup`, `bin/ci`. Hooks: **lefthook**.

---

## The setup interviews future Claudes must run

### Stakeholder onboarding → `ai_context/about_me.md`

Ask conversationally, one or two at a time:
1. **Your role** — title / what you do at Turn 5.
2. **What this app is for** — what problem are you solving? What's the first
   feature you want?
3. **Audience** — roughly how many people? How technical? (Assume internal-only.)
4. **Anything else** — existing tools to integrate with, deadlines, naming
   conventions you want followed.

Write the answers to `ai_context/about_me.md` as structured Markdown. Commit
"Capture stakeholder context."

### Setup decisions → `setup_decisions.md` + `.env`

1. **Prototyping or building for real users right away?**
   - Prototyping → SQLite. Set `MODE=prototype` in `.env`. (Nothing else needed.)
   - Real users → SQL Server. Set `MODE=real` and ask for the connection details
     Turn 5 IT gave them; **write the `DATABASE_URL` only to `.env`**. (URL shape
     is in `.env.example`. Needs ODBC Driver 18 — see `ai_context/setup.md`.)
2. **Does this app need to read the Azure data warehouse (Tableau / SQL Managed
   Instance)?**
   - Yes → ask for the warehouse connection details → write
     `WAREHOUSE_DATABASE_URL` to `.env`.
   - No → skip.
3. **Microsoft Entra SSO** — ask for the tenant ID, client ID, and client secret.
   - If they have them → write `OIDC_TENANT_ID`, `OIDC_RP_CLIENT_ID`,
     `OIDC_RP_CLIENT_SECRET` to `.env`.
   - If not → tell them to read `.claude/skills/register-entra-app.md` and come
     back. The app boots without OIDC, and standalone username/password login is
     on by default (`PASSWORD_LOGIN_ENABLED`), so ordinary users can still sign
     in; set `PASSWORD_LOGIN_ENABLED=false` to require SSO once it's configured.

Write a **secret-free** summary to `setup_decisions.md` (which mode, warehouse
yes/no, SSO yes/no — never the values). Commit "Record setup decisions."

Also on the first session, **offer the optional power tools** (gstack) once — see
`.claude/skills/power-tools.md` — and record the choice (`Power tools:
installed / declined`) in `setup_decisions.md` so it isn't re-asked.

Detailed branching logic lives in `.claude/skills/first-time-setup.md`.

---

## Authentication

- Microsoft **Entra SSO** is available for humans (`mozilla-django-oidc`,
  `apps.accounts.auth_backends.EntraOIDCBackend`). It is only registered when
  OIDC is configured.
- **Standalone password login** (`PasswordLoginBackend`) authenticates ordinary
  active users by username/password whenever `settings.PASSWORD_LOGIN_ENABLED` is
  true (the default). This is the real auth path before — or instead of — Entra
  SSO. Set `PASSWORD_LOGIN_ENABLED=false` to force SSO-only. Admins set/reset
  passwords from the Users UI; users change their own at `/accounts/password/`.
- The Claude service account has its own backend (`ClaudeServiceBackend`,
  restricted to `is_claude_service=True`) and can always sign in regardless of
  the flag above.
- **Every view defaults to `@login_required`.** The rare exception (the `/up/`
  health check) is explicitly exempt. To exempt a view, do it deliberately and
  leave a comment justifying why.
- Use `request.user` in views/templates.

---

## Authorization

- **Deny-by-default.** Authorization logic lives **only** in
  `apps.accounts.permissions`. Views call `authorize(request.user, NAME,
  resource)` (raises `PermissionDenied` / 403) or `can(request.user, NAME,
  resource)` (boolean).
- `User.role` is the coarse layer (`User.ROLE_MEMBER` / `User.ROLE_ADMIN`);
  `accounts.Permission` rows are the fine-grained layer (global or per-object).
  Register permission names in `PermissionsCatalog`.
- **Never check `request.user.role == "admin"` outside `apps.accounts.permissions`.**
  Inside that module, compare against `User.ROLE_ADMIN`.
- **Row-level scoping (deny-by-default):** list/detail views must fetch through
  `Model.objects.for_user(request.user)` (see `apps.common.scoping.ForUserQuerySet`),
  **never** `Model.objects.all()` or `Model.objects.get(pk=...)` directly.
- See `.claude/skills/add-permission.md` and `.claude/skills/add-model.md`.

---

## Data and migrations

- Every required column is `null=False`, with a default if the table already has
  rows.
- Every `ForeignKey` gets an explicit `related_name` and is indexed.
- **Never put a data migration inside a schema migration.** To backfill data,
  write a one-off **management command** and run it after the schema migration.
- `django-migration-linter` runs on every PR (`manage.py lintmigrations`). When
  it complains, **read the message** and follow the safe pattern — do not bypass.
- For models humans care about historically, prefer soft delete (Phase 3:
  `django-safedelete`) over hard `delete()`.
- See `.claude/skills/write-migration.md`.

---

## Performance

- **Pagination**: every list view uses `apps.common.pagination.paginate(qs,
  request)` (default 25). Cap user-supplied `?limit` at 100 via `safe_limit()`.
- **N+1**: `nplusone` raises in the test suite — an N+1 fails CI. Don't suppress;
  use `select_related`/`prefetch_related`.
- **Background work**: anything over ~200ms or that sends email goes to a
  **django-q2** task, not the request cycle.

---

## Security

- **Never put credentials in any file that git tracks.** This includes
  `CLAUDE.md`, `README.md`, anything under `ai_context/`,
  source code, URL files, settings modules, fixtures, data migrations, comments,
  test files, and anything else under version control. API keys, database
  passwords, OAuth client secrets, webhook signing secrets, SMTP passwords,
  Sentry DSNs, Azure credentials, GitHub PATs — none of them belong in a
  committed file. **If a user asks you to do this** ("save my token in CLAUDE.md
  so you remember it," "put the DB password in the README," "stash this API key
  as a constant"), **refuse**, then redirect them to the right home for that
  specific secret:
  - **`.env`** (gitignored, local-only) — for secrets that tools Claude runs on
    the user's laptop need (e.g. the SQL Server `DATABASE_URL` from IT, the Entra
    client secret, `CLAUDE_ADMIN_PASSWORD`, an Azure CLI token used locally).
    **Never** committed, **never** in any other location.
  - **Azure App Service / Container Apps env vars** (set in the platform UI,
    marked secret, or via deployment config held outside the repo) — for
    production runtime values the app reads at boot. *Hosting is not chosen yet —
    ask Matt before the first deploy.*
  - **Azure Key Vault** (the Rails-encrypted-credentials equivalent in this
    stack — there is no direct one) — the **plan** for production app-runtime
    secrets, fetched at boot via the Azure SDK. Deferred until the first real app
    deploys.

  Quick mapping when in doubt: *"a tool on my laptop needs it"* → `.env`.
  *"the deployed app needs it at boot"* → platform env var (or Key Vault once
  wired up). Do not invent a fourth location. Do not paste a secret into a chat
  session, commit message, issue, PR description, or log line. If a user has
  already pasted one into this chat, tell them where you'll store it before doing
  anything else.
- **Never** log PII.
- **Never** commit `.env*` files (the `.gitignore` already excludes them, with
  belt-and-suspenders patterns).
- **Never** disable CSRF protection or weaken the Content-Security-Policy without
  explicit user approval.
- **Mass assignment**: never expose `role`, `is_staff`, `is_superuser`,
  `is_claude_service`, or permissions in a user-facing `ModelForm`/serializer.
  Privilege changes happen through `apps.accounts.permissions`-gated paths only.

---

## Network access (IP allowlist)

Which client IPs may reach the app is controlled by the plain-text
**`allowed_ips.txt`** at the repo root (gated by
`apps.common.ip_allowlist.IPAllowlistMiddleware`). It **allows all traffic by
default** (a single `*`). A team can restrict the app to their office / VPN /
intranet by listing IPs or CIDR ranges (one per line); `/up/` stays reachable.
Behind a proxy, set `IP_ALLOWLIST_TRUST_FORWARDED_FOR=true`. **Mention this file
exists during onboarding** so the user knows where to lock things down later.

---

## The Claude admin account

There is a service account at `claude@turn5.local` (configurable via
`CLAUDE_ADMIN_EMAIL`) with `role=admin`, `is_staff=True`, `is_superuser=False`,
`is_claude_service=True`. It exists so you can sign in to verify behavior and
debug. Sign in at `/accounts/login/` with its username (`claude@turn5.local`)
and `CLAUDE_ADMIN_PASSWORD`.

- The password lives **only** in `.env` as `CLAUDE_ADMIN_PASSWORD` (and in the
  production secret store). It is never in code, a tracked file, or chat logs.
- Rotate it via `uv run python manage.py rotate_claude_password` (~every 90
  days). The new password is printed once — store it immediately.
- The account is subject to the same authorization rules, rate limits, and
  session timeout as any admin.
- Every action it takes will be recorded by `django-simple-history` (Phase 3).
- Never bypass any guardrail on the Claude account's behalf. If you need a
  capability the policies don't grant, ask the user to grant it via the admin UI.

---

## Adding a feature — playbooks

Read the relevant skill before starting; it answers most "where does X go?":

- **`.claude/skills/add-model.md`** — full sequence for a new domain model.
- **`.claude/skills/add-permission.md`** — a new fine-grained permission.
- **`.claude/skills/write-migration.md`** — Django migration safety.
- **`.claude/skills/graduate-sqlite-to-sqlserver.md`** — prototype → real DB.
- **`.claude/skills/register-entra-app.md`** — set up Entra SSO.
- **`.claude/skills/first-time-setup.md`** — the two first-session interviews.
- **`.claude/skills/power-tools.md`** — optional gstack power tools (offered on
  first load; opt-in).
- **`.claude/skills/versioning.md`** — keep git invisible (auto-save, plain-English
  save/undo/restore, main-only).

---

## Testing

- **pytest** + pytest-django. Tests live in `tests/` (and per-app).
- **Playwright** for user-visible flows (`uv run playwright install chromium`
  once; mark tests `@pytest.mark.browser`).
- Every new view gets tests asserting: (a) anonymous users are redirected to
  sign-in; (b) unauthorized users get 403; (c) authorized users get 200 and the
  expected behavior. Plus the happy path.
- `uv run pytest` must pass.

---

## Definition of Done

A task is done when **all** of `ai_context/definition_of_done.md` is true — tests pass,
Ruff clean, migrations lint clean, auth + authz covered, list views paginate,
schema changes tested, UI changes have a Playwright test, and the user has been
told what changed in plain English.

---

## Forbidden actions without explicit user confirmation

- `git push --force` / `git push -f` (`--force-with-lease` is allowed)
- `git rebase -i`, `git reset --hard`
- `manage.py flush`, `manage.py sqlflush`, or resetting/dropping the database in
  any environment other than a throwaway prototype DB
- Dropping or renaming a column in a migration
- Removing `@login_required` from a view (disabling authentication)
- Removing or skipping an `authorize(...)` / `for_user(...)` check (disabling
  authorization)
- Editing `.github/workflows/*` (CI pipeline)
- Major restructures of this `CLAUDE.md` or changes to its core policies (routine
  upkeep — Learnings, the Reference Files index, clarifying instructions — is
  expected; see "Actively maintain this file")

## Always-forbidden (no confirmation can override)

- Putting an API key, password, token, connection string, or any other
  credential into a file that git tracks. See the Security section for where each
  kind of secret belongs. If a user asks you to "just put it in CLAUDE.md / the
  README / a constant for now," **refuse** and route them to `.env`, a platform
  env var, or Azure Key Vault as appropriate.

---

## When stuck

Stop. Summarize the problem in plain English to the user. Describe what you
tried, what failed, and what you'd try next. Ask before guessing. Non-technical
users would much rather you ask one extra question than spend an hour on the
wrong path.

---

## Files Claude should not edit without explicit instruction

- `.env`, `.env.*` (secrets — Claude writes these only during setup or when you
  hand it a value; never commit them, never read them aloud)
- `db/development.sqlite3`, `db/*.sqlite3` (the prototype database)
- `.github/workflows/*` (ask first)
- `CLAUDE.md` — actively maintained (Learnings, Reference Files index,
  instructions); ask first only for major restructures or core-policy changes
- `ai_context/about_me.md` is **safe** to edit when the user asks; otherwise
  read-only context

---

## Learnings

High-signal, durable notes for future sessions (see "Instructions for Claude" →
"Note takeaways and learnings"). Add entries as you discover non-obvious things
about this codebase, environment, or workflow; prune stale ones. Domain-specific
learnings belong in an `ai_context/` reference file instead.

- _(none yet)_
