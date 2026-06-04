"""
Base settings shared by every environment.

Environment-specific modules import everything from here and override:
  - config.settings.dev  — local development (reads .env; SQLite or SQL Server)
  - config.settings.prod — production (DEBUG off, secure cookies, HSTS)

Secrets are read from the environment (.env locally; platform env vars / Azure
Key Vault in production). NOTHING secret is hard-coded here. See CLAUDE.md →
Security for the rules on where credentials are allowed to live.
"""

from pathlib import Path

import environ

# config/settings/base.py -> repo root is three parents up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Reads BASE_DIR/.env if present. Safe (no-op) when the file is absent.
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
# A dev-insecure default lets the template boot with zero config. prod.py
# requires SECRET_KEY to come from the environment (see that module).
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-template-default-CHANGE-ME-in-.env-or-prod-env-vars",
)

# Overridden to True in dev.py, forced False in prod.py.
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # whitenoise.runserver_nostatic must precede staticfiles so WhiteNoise
    # serves static assets in development too.
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Third party
    "guardian",  # per-object permissions
    "simple_history",  # audit trail (paper_trail equivalent)
    "django_htmx",
    "django_q",  # background jobs (DB-backed)
    "django_tailwind_cli",  # Tailwind via standalone CLI (no Node)
    "mozilla_django_oidc",  # Microsoft Entra SSO
    "django_migration_linter",  # `manage.py lintmigrations` (strong_migrations analog)
    # Local
    "apps.accounts",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Network allowlist (allowed_ips.txt). Allow-all by default; gates everything
    # except /up/. Placed early so blocked IPs never reach app logic.
    "apps.common.ip_allowlist.IPAllowlistMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # mozilla_django_oidc.SessionRefresh is inserted here *only when OIDC is
    # configured* (see below) — it would otherwise try to refresh sessions
    # against unset endpoints and break the Claude service account.
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    # django_htmx middleware must be last.
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.nav_capabilities",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database — default is the SQLite prototype DB. dev.py implements the
# MODE=prototype|real switch; prod.py reads DATABASE_URL. A second read-only
# "warehouse" connection is added when WAREHOUSE_DATABASE_URL is set.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db" / "development.sqlite3",
    }
}

# ---------------------------------------------------------------------------
# Authentication / Authorization
# ---------------------------------------------------------------------------
# Microsoft Entra (Azure AD) OIDC. Endpoints are derived from the tenant id.
# If OIDC_RP_CLIENT_ID is unset the OIDC backend is NOT registered; the template
# still boots and signs people in via standalone password login (below).
OIDC_TENANT_ID = env("OIDC_TENANT_ID", default="")
OIDC_RP_CLIENT_ID = env("OIDC_RP_CLIENT_ID", default="")
OIDC_RP_CLIENT_SECRET = env("OIDC_RP_CLIENT_SECRET", default="")
OIDC_ENABLED = bool(OIDC_RP_CLIENT_ID and OIDC_TENANT_ID)

# Standalone username/password login for ordinary users (the PasswordLoginBackend
# below). On by default so the app has real auth before — or instead of — Entra
# SSO. Set PASSWORD_LOGIN_ENABLED=false to force SSO-only once Entra is wired up.
# The Claude service account always authenticates regardless of this flag.
PASSWORD_LOGIN_ENABLED = env.bool("PASSWORD_LOGIN_ENABLED", default=True)

_tenant = OIDC_TENANT_ID or "common"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"
OIDC_OP_AUTHORIZATION_ENDPOINT = (
    f"https://login.microsoftonline.com/{_tenant}/oauth2/v2.0/authorize"
)
OIDC_OP_TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{_tenant}/oauth2/v2.0/token"
OIDC_OP_USER_ENDPOINT = "https://graph.microsoft.com/oidc/userinfo"
OIDC_OP_JWKS_ENDPOINT = f"https://login.microsoftonline.com/{_tenant}/discovery/v2.0/keys"
# Look users up / create them by email claim.
OIDC_USERNAME_ALGO = "apps.accounts.auth_backends.generate_username"
OIDC_STORE_ID_TOKEN = True

AUTHENTICATION_BACKENDS = [
    *(["apps.accounts.auth_backends.EntraOIDCBackend"] if OIDC_ENABLED else []),
    # Claude admin service account (password backend, restricted to service users).
    "apps.accounts.auth_backends.ClaudeServiceBackend",
    # Standalone username/password login for ordinary users. Self-gates on
    # PASSWORD_LOGIN_ENABLED at authenticate time (always registered so the flag
    # can be toggled at runtime / in tests).
    "apps.accounts.auth_backends.PasswordLoginBackend",
    # django-guardian per-object permissions.
    "guardian.backends.ObjectPermissionBackend",
]

if OIDC_ENABLED:
    # Insert SessionRefresh immediately after AuthenticationMiddleware.
    _auth_idx = MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
    MIDDLEWARE.insert(_auth_idx + 1, "mozilla_django_oidc.middleware.SessionRefresh")

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# django-guardian
GUARDIAN_RAISE_403 = True
ANONYMOUS_USER_NAME = None  # we never grant object perms to anonymous users

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        # The Claude service account password is machine-generated (>=32 chars);
        # human admins, if any, still get a sane floor.
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Content-Security-Policy (django-csp) — REPORT-ONLY for now. It surfaces
# violations in the browser console without breaking anything, so we can tighten
# safely. Phase 3 promotes this to an enforced `CONTENT_SECURITY_POLICY` (and
# swaps Alpine for its CSP build / adds nonces to drop 'unsafe-eval').
# ---------------------------------------------------------------------------
CONTENT_SECURITY_POLICY_REPORT_ONLY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        # Vendored HTMX/Alpine are same-origin ('self'). Alpine evaluates
        # expressions via eval(); report-only mode logs that so Phase 3 can fix it.
        "script-src": ["'self'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
        "object-src": ["'none'"],
    }
}

# ---------------------------------------------------------------------------
# The Claude admin service account (see apps/accounts + CLAUDE.md).
# ---------------------------------------------------------------------------
CLAUDE_ADMIN_EMAIL = env("CLAUDE_ADMIN_EMAIL", default="claude@turn5.local")

# ---------------------------------------------------------------------------
# Network allowlist (see allowed_ips.txt + apps/common/ip_allowlist.py).
# Default file allows all traffic; teams can restrict to their intranet.
# ---------------------------------------------------------------------------
IP_ALLOWLIST_FILE = env("IP_ALLOWLIST_FILE", default=str(BASE_DIR / "allowed_ips.txt"))
# Set true in production behind a TRUSTED proxy so the real client IP (first
# X-Forwarded-For entry) is checked instead of the proxy's address.
IP_ALLOWLIST_TRUST_FORWARDED_FOR = env.bool("IP_ALLOWLIST_TRUST_FORWARDED_FOR", default=False)
# CLAUDE_ADMIN_PASSWORD is intentionally NOT given a default. It is read from
# the environment by the provisioning migration and AccountsConfig.ready().

# ---------------------------------------------------------------------------
# Background jobs (django-q2, DB broker — no Redis)
# ---------------------------------------------------------------------------
Q_CLUSTER = {
    "name": "turn5",
    "orm": "default",
    "workers": 2,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "catch_up": False,
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (WhiteNoise) + Tailwind CLI
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Plain storage in base/dev (no manifest needed). prod.py swaps in WhiteNoise's
# compressed + hashed manifest storage (which requires `collectstatic`).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# django-tailwind-cli: the standalone binary is cached here (gitignored).
TAILWIND_CLI_PATH = ".django_tailwind_cli/"
# Tracked Tailwind input stylesheet (custom @font-face / @theme live here).
# Without this, the CLI falls back to an auto-generated source.css that it
# overwrites on every build — so customizations must live in this tracked file.
# Compiles to STATICFILES_DIRS[0]/css/tailwind.css (the gitignored artifact).
TAILWIND_CLI_SRC_CSS = "static/css/source.css"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Messages -> Tailwind colour names (used by templates/components/_flash.html)
# ---------------------------------------------------------------------------
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {
    message_constants.DEBUG: "slate",
    message_constants.INFO: "sky",
    message_constants.SUCCESS: "emerald",
    message_constants.WARNING: "amber",
    message_constants.ERROR: "rose",
}

# ---------------------------------------------------------------------------
# Email — console in dev; prod overrides via env. (SMTP provider TBD; see
# ai_context/architecture.md and the open questions in the build spec.)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@turn5.local")
