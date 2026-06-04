# Architecture

This document has two parts:

1. **Current architecture** — what the template actually ships with today. Faithful and accurate as of this commit.
2. **Planned (Phase 3)** — documented *future* plans. **None of the Phase 3 items are built yet.** They are an outline so a future Claude Code session (or a reviewer) knows the intended direction. Each is marked **DEFERRED**.

If you are a future Claude Code session: only Part 1 describes code that exists. Do not assume any Part 2 capability is present.

---

## Part 1 — Current architecture

### Stack at a glance

- **Python 3.13** (pinned via `.python-version`), package manager **uv**. Everything runs through uv: `uv run python manage.py <cmd>`, `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format`, `uv run mypy .`. **No Node/npm anywhere.**
- Convenience scripts: `bin/setup` (first run) and `bin/ci` (full check suite).
- Pre-commit hooks via **lefthook** (`uv run lefthook install`).

### Settings split + dual-DB via `MODE`

Settings live in `config/settings/{base,dev,prod}.py`:

- `manage.py` defaults to `config.settings.dev`.
- `wsgi.py` / `asgi.py` default to `config.settings.prod`.

The `MODE` environment variable selects the database:

| `MODE`        | Database                                              |
| ------------- | ---------------------------------------------------- |
| `prototype` (default) | SQLite at `db/development.sqlite3` — zero setup |
| `real`        | SQL Server via `DATABASE_URL`                        |

Optional read-only analytics warehouse via `WAREHOUSE_DATABASE_URL` (Django DB alias `warehouse`).

SQL Server `DATABASE_URL` shape:

```
mssql://USER:PASSWORD@SERVER:1433/DBNAME?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
```

All config is read from `.env` via **django-environ**. `.env` is gitignored; `.env.example` holds keys only (never values).

### `apps.accounts` — identity, permissions, authorization

**Custom user** `apps.accounts.models.User(AbstractUser)` (`AUTH_USER_MODEL = "accounts.User"`):

- `role` — choices `member` / `admin` (constants `User.ROLE_MEMBER`, `User.ROLE_ADMIN`; default `member`).
- `is_claude_service` — bool.
- `user.can(permission_name, resource=None) -> bool` — admins always `True`; otherwise needs a matching `Permission` row; a global check requires a global grant.

**Permission model** `apps.accounts.models.Permission` (`user` FK, `related_name="permissions"`, `name`, `resource_type`, `resource_id`):

- `UniqueConstraint` on `(user, name, resource_type, resource_id)`; index on `(resource_type, resource_id)`.
- Null `resource_type` + `resource_id` → **global grant**. Both set → **per-object grant**.

**Authorization is DENY BY DEFAULT** and lives **only** in `apps.accounts.permissions`:

- `PermissionsCatalog.register(name, description)` / `.all()` / `.choices()`; backed by a `REGISTRY` dict. Baseline constants: `MANAGE_USERS = "manage_users"`, `VIEW_ADMIN_DASHBOARD = "view_admin_dashboard"`.
- `can(user, name, resource=None) -> bool` — non-raising.
- `authorize(user, name, resource=None)` — raises Django `PermissionDenied` (403) unless allowed. **Call at the top of every mutating/scoped view.**

> **Hard rule:** never compare `user.role` outside `apps.accounts.permissions`. All role logic is centralized there.

### Row scoping — `for_user`

`apps.common.scoping.ForUserQuerySet` provides `.for_user(user)`:

- Admins see all rows; members see **none** by default.
- Subclass and override to grant member visibility per model.

> **Hard rule:** list/detail views MUST use `Model.objects.for_user(request.user)` — never `Model.objects.all()` or `.get(pk=...)` directly.

### Pagination

`apps.common.pagination`:

- `paginate(queryset, request, default=25)` → a Django `Page`.
- `safe_limit(requested, default=25, maximum=100)` → clamps a user-supplied `?limit`.
- Constants `DEFAULT_PAGE_SIZE = 25`, `MAX_PAGE_SIZE = 100`.

> **Rule:** every list view paginates.

### Authentication — password login + Entra SSO + Claude service account

Auth backends in `apps.accounts.auth_backends`:

- `EntraOIDCBackend` — Microsoft Entra SSO. Registered **only** when OIDC is configured. Env: `OIDC_TENANT_ID`, `OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET` (endpoints derived from the tenant: `login.microsoftonline.com` / `graph.microsoft.com/oidc/userinfo`).
- `ClaudeServiceBackend` — password backend that authenticates **only** users with `is_claude_service=True` (always on).
- `PasswordLoginBackend` — standalone username/password for ordinary active users; gated by `PASSWORD_LOGIN_ENABLED` (default true).

The app **boots without OIDC**: standalone username/password login is on by default, so ordinary users can sign in before SSO (set `PASSWORD_LOGIN_ENABLED=false` to require SSO). See [auth.md](auth.md). Every view defaults to `@login_required`.

**Claude admin service account:**

- Username & email = `claude@turn5.local` (`CLAUDE_ADMIN_EMAIL`).
- `is_staff=True`, `is_superuser=False`, `role=admin`, `is_claude_service=True`.
- Password lives **only** in env `CLAUDE_ADMIN_PASSWORD` (never a tracked file).
- Provisioned idempotently by data migration `apps/accounts/migrations/0002_provision_claude_admin.py` (sets an unusable password if the env var is unset).
- **Prod guard:** `AccountsConfig.ready()` raises `ImproperlyConfigured` if `DEBUG=False` and the password is unset.
- Rotate with `uv run python manage.py rotate_claude_password` (32-char random, printed once, ~every 90 days).
- Sign-in: `/accounts/login/` (username `claude@turn5.local` + `CLAUDE_ADMIN_PASSWORD`).

### URLs

| Path                | What                                                            |
| ------------------- | -------------------------------------------------------------- |
| `/`                 | index — hello world, `@login_required`, plain text `Hello, <email>!` |
| `/accounts/login/`  | Django `LoginView`, template `accounts/login.html`             |
| `/accounts/logout/` | POST                                                           |
| `/accounts/profile/`| profile page                                                   |
| `/up/`              | health check — 200 `OK`, **no auth**                            |
| `/oidc/`            | `mozilla_django_oidc.urls`                                      |
| `/admin/`           | Django admin                                                    |

### Frontend — no Node

- **Tailwind** via **django-tailwind-cli** (standalone binary, no Node). Build: `uv run python manage.py tailwind build`. In templates: `{% load tailwind_cli %}{% tailwind_css %}`. Output `static/css/tailwind.css` (a gitignored build artifact).
- **HTMX 2.0.4** + **Alpine 3.14.8** vendored in `static/vendor/`.
- Templates in `templates/`: `base.html`, `components/_nav.html`, `components/_flash.html`, `accounts/login.html`, `accounts/profile.html`.
- Flash colours via `MESSAGE_TAGS`: success = emerald, warning = amber, error = rose, info = sky, debug = slate.

### Background jobs + supporting libraries

- **Background jobs:** **django-q2** (`Q_CLUSTER`, ORM broker, **no Redis**).
- **Audit:** **django-simple-history** installed (model history itself is a Phase 3 task — see Part 2).
- **Migration safety:** **django-migration-linter** — `uv run python manage.py lintmigrations`.
- **N+1 detection:** **nplusone**.
- **Rate limiting:** **django-ratelimit**.
- **CSP:** **django-csp** (enforcement is Phase 2).
- **Tests:** **pytest** + **pytest-django**; browser tests via **Playwright** (pytest marker `browser`; needs `uv run playwright install chromium`).

### Network allowlist

`apps.common.ip_allowlist.IPAllowlistMiddleware` gates every request (except
`/up/`) against the plain-text **`allowed_ips.txt`** at the repo root:

- Default file contains `*` → **allow all** (nothing restricted out of the box).
- Entries are single IPs or CIDR ranges, one per line; comments with `#`.
- Edits are picked up live (re-read when the file's mtime changes — no redeploy).
- Behind a proxy, set `IP_ALLOWLIST_TRUST_FORWARDED_FOR=true` so the real client
  IP (first `X-Forwarded-For`) is checked, not the proxy's.

Lets a Turn 5 team restrict an app to their office / VPN / intranet by editing
one file. (Future option: ship a non-`*` default that only allows the company
intranet.)

### Request flow (typical authenticated view)

1. The IP allowlist middleware checks the client IP (allow-all by default; 403 if
   the app has been restricted and the IP isn't approved).
2. Request hits a view; `@login_required` redirects to `/accounts/login/` if anonymous.
3. View calls `authorize(request.user, <permission>, resource)` at the top for any mutating/scoped action (raises 403 if denied).
4. Data access goes through `Model.objects.for_user(request.user)` — never `.all()`/`.get()`.
5. List results pass through `paginate(...)` (with `safe_limit(...)` for any user `?limit`).
6. Template renders via `base.html` (Tailwind + vendored HTMX/Alpine), flashes styled by `MESSAGE_TAGS`.
7. Long-running work is offloaded to **django-q2**.

### Where secrets live (three buckets)

1. **`.env`** (local dev) — read by django-environ. Gitignored; `.env.example` holds keys only.
2. **Platform environment variables** (the hosting platform's config) — the prod equivalent of `.env`; same keys, injected by the host.
3. **Azure Key Vault** — for the most sensitive material (e.g. the future field-level encryption key, see Part 2). Surfaced to the app as environment variables by the platform.

No secret is ever committed to the repo.

---

## Part 2 — Planned (Phase 3, **not yet built**)

> Everything below is an **outline of intended future work**. None of it is implemented in this template today. Each item is **DEFERRED**. Do not assume any of these capabilities exist.

### Error tracking — Sentry with PII scrubbing — **DEFERRED**

Wire up Sentry for error and performance monitoring, configured with **PII scrubbing** (strip emails, names, tokens, and request bodies before send) so Turn 5 internal data never leaves in a stack trace. DSN via env (`.env` / platform env var).

### Audit logging — django-simple-history + prune job — **DEFERRED**

django-simple-history is already installed but no models are tracked yet. Plan:

- Enable history on `apps.accounts.User`, `apps.accounts.Permission`, and other sensitive models.
- Add a recurring **django-q2** scheduled job to **prune** history older than the retention window (**default 1 year**).

### Structured logging — python-json-logger — **DEFERRED**

Replace plain-text logs with structured **JSON logging** via **python-json-logger** so logs are queryable by the hosting platform / log aggregator (one JSON object per line, with request id, user id, and level).

### Soft delete — django-safedelete — **DEFERRED**

Adopt **django-safedelete** for soft deletion on models where records must be recoverable / auditable rather than hard-deleted. Must compose cleanly with `for_user` scoping (deleted rows excluded from normal querysets).

### Field-level encryption — django-cryptography — **DEFERRED**

Encrypt sensitive fields at rest with **django-cryptography**, with the **encryption key stored in Azure Key Vault** (bucket 3 above), never in the repo or a tracked file.

### CSP enforce mode — django-csp — **DEFERRED**

django-csp is installed; Phase 2 introduces report-only headers. Phase 3 moves CSP to **enforce mode** with a tightened policy once report data confirms no legitimate resources are blocked.

### Deeper health endpoint — **DEFERRED**

Today `/up/` returns a flat 200 `OK` with no auth. Phase 3 adds a deeper health endpoint that actively checks the **primary database** and the optional **warehouse** connection, reporting per-dependency status.

### Backup pattern — **DEFERRED**

Define a backup strategy for the SQL Server database and any persisted artifacts. The concrete approach **depends on the hosting platform** (e.g. managed Azure SQL automated backups vs. a self-managed dump job), so it is documented as a pattern to be finalized at deploy time rather than a fixed implementation.
