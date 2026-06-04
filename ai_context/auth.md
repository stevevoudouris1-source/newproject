# Auth & user management

Everything about how users sign in, what they're allowed to do, and the UI for
managing them. Read this before touching `apps/accounts/`; it should save you
from auditing the code. Keep it in sync when you change the module.

## Key files

| File | Role |
|---|---|
| `apps/accounts/auth_backends.py` | The three authentication backends |
| `apps/accounts/models.py` | `User` (role, is_claude_service), `Permission`, scoped `UserManager` |
| `apps/accounts/permissions.py` | `PermissionsCatalog`, `can()`, `authorize()` |
| `apps/accounts/forms.py` | `UserForm` (create/edit + password + permission grants) |
| `apps/accounts/views.py` | login, profile, change_password, user CRUD |
| `apps/accounts/context_processors.py` | `nav_capabilities` (nav link visibility) |
| `apps/accounts/urls.py` | routes (login/logout/profile/password + `/users/...`) |
| `templates/accounts/` | `login.html`, `profile.html`, `change_password.html`, `users/{list,detail,form}.html` |
| `config/settings/base.py` | `AUTHENTICATION_BACKENDS`, `PASSWORD_LOGIN_ENABLED`, `OIDC_ENABLED`, validators |
| `apps/accounts/tests/` | `test_password_login.py`, `test_user_management.py` |

## Authentication (how sign-in works)

Three backends, tried in this order (`config/settings/base.py` → `AUTHENTICATION_BACKENDS`):

1. **`EntraOIDCBackend`** — Microsoft Entra SSO. Registered **only when OIDC is
   configured** (`OIDC_ENABLED = bool(OIDC_RP_CLIENT_ID and OIDC_TENANT_ID)`).
2. **`ClaudeServiceBackend`** — password login restricted to the Claude service
   account (`is_claude_service=True`). **Always on**, independent of any flag.
3. **`PasswordLoginBackend`** — standalone username/password for ordinary, active
   users. Self-gates on **`settings.PASSWORD_LOGIN_ENABLED`** (env, default
   `True`). Excludes the service account (that's backend #2's job).

So today, with no OIDC configured, ordinary users sign in with username/password.
Set `PASSWORD_LOGIN_ENABLED=false` to force SSO-only once Entra is wired up.

- Login view: `RateLimitedLoginView` (`/accounts/login/`), **rate-limited 5/min/IP**.
  It shows the password form by default and the "Sign in with Microsoft" button
  **only when `OIDC_ENABLED`** (passed to the template as `oidc_enabled`).
- Passwords are checked against `AUTH_PASSWORD_VALIDATORS` (min length 12, common,
  numeric, similarity).

## Authorization (what users can do)

Two layers, **deny-by-default**, all logic in `apps/accounts/permissions.py`:

- **Role** — `User.role` is `member` or `admin`. **Admins implicitly pass every
  check** (`User.can()` short-circuits).
- **Fine-grained permissions** — `Permission` rows (`apps/accounts/models.py`),
  registered in `PermissionsCatalog`. A row is a **global** grant when
  `resource_type`/`resource_id` are null, or **per-object** when both are set.
  Catalog today: `view_users`, `manage_users`, `view_admin_dashboard`.

How to enforce (never compare `user.role` outside this module):
- `authorize(user, NAME, resource=None)` → raises `PermissionDenied` (403) unless allowed. Gate actions with it.
- `can(user, NAME, resource=None)` → bool, for branching/templates.
- Row scoping: fetch lists via `Model.objects.for_user(user)`, never `.all()`.
  `User` has a `UserManager` (built with `DjangoUserManager.from_queryset(UserQuerySet)`
  so `create_user` etc. still work) whose `for_user` returns all users to viewers/
  managers, none to everyone else.

See `.claude/skills/add-permission.md` to add a permission.

## User management UI

Gated views (`apps/accounts/views.py`, routes in `urls.py`):

| Route | View | Gate |
|---|---|---|
| `/users/` | `user_list` | `view_users` |
| `/users/<pk>/` | `user_detail` | `view_users` |
| `/users/new/` | `user_create` | `manage_users` |
| `/users/<pk>/edit/` | `user_edit` | `manage_users` |
| `/accounts/profile/` | `profile` | login only |
| `/accounts/password/` | `change_password` | login + has usable password + `PASSWORD_LOGIN_ENABLED` |

- **`UserForm`** edits `username, email, first_name, last_name, is_active`, an
  optional `password1`/`password2` (admin sets/resets; blank on edit = unchanged),
  and two checkboxes — `can_view_users` / `can_manage_users` — that sync the
  matching global `Permission` rows. **Manage implies view** (ticking manage grants
  both).
- **Self-service**: users change their own password at `/accounts/password/`
  (Django's `PasswordChangeForm`; session kept via `update_session_auth_hash`).
- The **nav "Users" link** shows only to permitted users, via the
  `nav_capabilities` context processor (`nav_can_view_users` / `nav_can_manage_users`).

## Gotchas / invariants

- **Mass assignment:** `UserForm` deliberately never exposes `role`, `is_staff`,
  `is_superuser`, or `is_claude_service`. Don't add them — privilege changes go
  through the permission grants only.
- **Service account is protected:** `user_edit` refuses to edit a user with
  `is_claude_service=True`; `PasswordLoginBackend` refuses to authenticate it.
- **New users without a password** get an unusable password (`set_unusable_password`)
  and can't sign in until one is set — humans on SSO never need one.
- **Tests:** rate limiting is off (`RATELIMIT_ENABLE=False`) except the dedicated
  rate-limit test, which freezes the clock django-ratelimit reads to avoid a
  window-boundary flake. Auth tests using shared fixtures define them locally
  (the `tests/conftest.py` fixtures don't reach `apps/accounts/tests/`).

## Related

- `CLAUDE.md` → Authentication / Authorization (policy).
- `CHANGELOG.md` (2026-06-04) — when this module was added.
