# Changelog

This file has two parts:

1. **Application specification** — a holistic, always-current description of what
   the app does today. Update it whenever a feature or behaviour changes.
2. **Changelog** — dated, append-only entries summarizing non-trivial changes so
   they can be referenced later. Skip purely cosmetic tweaks (e.g. a colour or
   spacing change).

Maintained by Claude per the rules in [CLAUDE.md](CLAUDE.md).

---

## Application specification

Turn 5 internal-tools starter app — Django 5 / Python 3.13 / uv. Internal,
single-tenant, deny-by-default.

**Authentication** (`apps/accounts/auth_backends.py`)
- **Standalone username/password login** for ordinary users, on by default
  (`PASSWORD_LOGIN_ENABLED`); set false to force SSO-only. Login is rate-limited
  (5/min/IP) and passwords are validated against Django's validators.
- **Microsoft Entra SSO** — registered only when OIDC is configured.
- **Claude service account** — its own always-on password backend.

**Authorization** (`apps/accounts/permissions.py`)
- Two layers: `User.role` (member/admin) + fine-grained `Permission` rows, plus
  django-guardian. Admins implicitly pass every check.
- Catalog permissions: `view_users` (read-only), `manage_users`
  (create/edit + grant), `view_admin_dashboard`.
- Row scoping via `Model.objects.for_user(user)`; list views paginate.

**User management UI** (gated on the permissions above)
- `/users/` list, `/users/<pk>/` detail, `/users/new/` create, `/users/<pk>/edit/`.
- Admins set/reset passwords on the create/edit form (mass-assignment-safe: no
  role/staff/superuser/service fields exposed). The Claude service account can't
  be edited here.
- Users change their own password at `/accounts/password/`.

**3D facility tour** (`apps/tours`, see `ai_context/tours.md`)
- `/tour/` embeds a Matterport 3D walkthrough for any signed-in user, with an
  "Open in a new tab" fallback. Linked from the nav bar as "3D Tour".

**Pages & chrome**
- Landing (`/`) — orientation page rendered in `base.html`.
- Profile (`/accounts/profile/`), login (password form by default; Entra button
  only when OIDC is configured), nav bar with a Users link for permitted users.
- Tailwind (via django-tailwind-cli, no Node) + HTMX + Alpine, vendored; Inter
  font + Lucide icons.

**Security & ops**
- IP allowlist (`allowed_ips.txt`, allow-all by default), CSP (report-only;
  the only embeddable third-party host is `my.matterport.com`),
  CSRF, secrets only in `.env`.
- Data: SQLite (prototype) or SQL Server (real) via `MODE`.
- Tests: pytest + pytest-xdist; CI gate in `bin/ci` (ruff, format, mypy,
  migration-linter, pytest). A guard test fails the build on multi-line
  `{# #}` template comments.

---

## Changelog

### 2026-11-15
- Added the embedded Matterport 3D tour page at `/tour/` (new `apps.tours`), a
  "3D Tour" nav link, and a CSP `frame-src` allowance for `my.matterport.com`.
- Captured stakeholder context and setup decisions (prototype / SQLite).

### 2026-06-04

- **Proportional testing + auto-backup hook.** "Don't over-test": minor tweaks
  (copy, styling, docs, config) no longer require new tests or a full test run —
  TDD + `bin/ci` are reserved for behavioral/substantial changes (CLAUDE.md,
  definition_of_done.md, and the versioning skill updated). Moved the full test
  suite off the pre-push hook to CI on `main`, and added a `post-commit`
  auto-backup hook (non-blocking) so every save is pushed instantly.

- **Git made invisible for non-technical users.** New `versioning` skill +
  CLAUDE.md "Version control — keep it invisible" section: Claude auto-saves and
  auto-backs-up after each change, works **main-only by default** (no
  branches/worktrees/PRs unless the user explicitly asks), speaks plain English
  (save / back up / undo / go back — never commit/push/branch), and undo is
  forward-only (never `reset --hard`). Added `bin/save` (stage + commit + push
  with plain-English output) and a "You don't need to learn git" README section;
  reframed branch protection as an opt-in team setup.

- **Guardrail tuning (`.claude/settings.json`).** Hard-deny now covers only
  destructive, irreversible ops: `git push --force`/`-f`, `git reset --hard`,
  `rm -rf`, and the `manage.py` flush/reset_db/sqlflush set. Removed over-broad
  denies that conflicted with documented flows: `.env` writes (onboarding writes
  secrets there), the CLAUDE.md edit-block (vs "actively maintain this file"),
  `git config`, `git rebase`, and `db/` writes. `--force-with-lease` is allowed
  (safe variant). CLAUDE.md wording aligned to match.

- **Docs auth-consistency sweep.** Corrected stale pre–password-login wording in
  CLAUDE.md and the `ai_context/` + skill docs: removed the obsolete
  `/accounts/login/?service=true` URL (the Claude account now signs in at
  `/accounts/login/`); replaced "only the Claude service account can sign in
  until SSO" with the current default (standalone password login on via
  `PASSWORD_LOGIN_ENABLED`); added `PasswordLoginBackend` to the architecture and
  stack overviews; fixed an `ai_reference/` → `ai_context/` typo; and added the
  missing `## Learnings` section that CLAUDE.md's own instructions reference.

- **Per-feature documentation practice.** Added a CLAUDE.md instruction to
  create a matching `ai_context/<feature>.md` doc for each substantial feature
  (written for future agents, kept in sync with the code) so agents can get up to
  speed without auditing the whole codebase. First examples:
  `ai_context/auth.md` (authentication, permissions, user management) and
  `ai_context/security.md` (IP allowlist, rate limiting, CSP, secrets, prod
  hardening), both indexed in CLAUDE.md.

- **Company context + data dictionary scaffolding.** Added Turn 5 background to
  CLAUDE.md (multi-brand DTC retailer — americanmuscle.com, americantrucks.com,
  extremeterrain.com, ecklers.com, throttl.com). Created `ai_context/data_dictionary.md`
  as a placeholder index, with an instruction for Claude to offer to build a
  data dictionary (per-domain files under `ai_context/data_dictionary/`) on first
  access to a company database/warehouse.

- **Docs consolidated under `ai_context/`.** Moved `docs/{SETUP,ARCHITECTURE,
  DEFINITION_OF_DONE}.md` → `ai_context/{setup,architecture,definition_of_done}.md`
  (lowercase), updated all references, removed `docs/`. Added a Reference Files
  index to CLAUDE.md and instructions for Claude to actively maintain CLAUDE.md,
  keep this changelog, and answer questions with text (not code).

- **Standalone password login.** Added `PasswordLoginBackend` (gated by
  `PASSWORD_LOGIN_ENABLED`, default on) so ordinary users sign in with a
  username/password before — or instead of — Entra SSO. Admins set passwords in
  the Users UI; users self-serve at `/accounts/password/`.

- **User management UI.** New `view_users` (read-only) permission alongside
  `manage_users`; list/detail/create/edit views, scoped `User` manager, nav link,
  and a mass-assignment-safe form. Surfaces the existing authorization layer that
  previously had no UI.

- **Landing page** now renders in `base.html` with framework-orientation content
  (replacing the bare hello-world). Login page shows the password form by default
  and the Microsoft button only when OIDC is configured.

- **Fixes.** Made the flaky `test_service_login_is_rate_limited` deterministic
  (froze the clock django-ratelimit reads — a time-window boundary, not cache
  sharing). Fixed multi-line `{# #}` template comments leaking as visible text and
  added `tests/test_templates.py` to fail CI if any reappear. Added
  `--force-exclude` to the ruff pre-commit hooks so generated migrations don't
  break commits.
