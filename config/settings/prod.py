"""
Production settings.

DEBUG is forced off. SECRET_KEY, ALLOWED_HOSTS and DATABASE_URL MUST come from
the environment (platform env vars / Azure Key Vault). Secure-cookie + HSTS
hardening is applied here (see Phase 2 of the build spec). Hosting target is
still TBD — ask Matt before the first deploy.
"""

from .base import *  # noqa: F403

DEBUG = False

# Fail loudly if the production secret key was not supplied.
SECRET_KEY = env("SECRET_KEY")  # noqa: F405  (raises ImproperlyConfigured if unset)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405  (required in prod)

# SQL Server (per-app schema provisioned by Turn 5 IT).
DATABASES = {"default": env.db_url("DATABASE_URL")}  # noqa: F405

WAREHOUSE_DATABASE_URL = env("WAREHOUSE_DATABASE_URL", default=None)  # noqa: F405
if WAREHOUSE_DATABASE_URL:
    DATABASES["warehouse"] = env.db_url("WAREHOUSE_DATABASE_URL")  # noqa: F405

# ---------------------------------------------------------------------------
# Security hardening (Phase 2). HTTPS is terminated by the platform; trust the
# X-Forwarded-Proto header it sets.
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Compressed + hashed static files served by WhiteNoise (run `collectstatic`).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Email backend in production comes from the environment once an SMTP / Graph
# provider is chosen (open question for Matt). Defaults to console until then.
EMAIL_BACKEND = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
