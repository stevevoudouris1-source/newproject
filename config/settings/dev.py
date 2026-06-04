"""
Development settings — local laptops.

Reads .env. Picks the database from MODE:
  MODE=prototype  -> SQLite single file (zero setup; the first-day default)
  MODE=real       -> SQL Server via DATABASE_URL (per-user schema from Turn 5 IT)

A second read-only "warehouse" connection is added when WAREHOUSE_DATABASE_URL
is set (opt-in per app; Azure SQL Managed Instance).
"""

import logging

from .base import *  # noqa: F403

DEBUG = env.bool("DEBUG", default=True)  # noqa: F405

ALLOWED_HOSTS = env.list(  # noqa: F405
    "ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"]
)

MODE = env("MODE", default="prototype")  # noqa: F405

if MODE == "prototype":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db" / "development.sqlite3",  # noqa: F405
        }
    }
else:
    # MODE=real -> SQL Server. DATABASE_URL is provided by Turn 5 IT and lives
    # ONLY in .env (never committed). Shape is documented in .env.example.
    DATABASES = {"default": env.db_url("DATABASE_URL")}  # noqa: F405

WAREHOUSE_DATABASE_URL = env("WAREHOUSE_DATABASE_URL", default=None)  # noqa: F405
if WAREHOUSE_DATABASE_URL:
    DATABASES["warehouse"] = env.db_url("WAREHOUSE_DATABASE_URL")  # noqa: F405

# Email to the console in development.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Make missing static files a hard error in dev so they are caught before prod.
WHITENOISE_USE_FINDERS = True

# N+1 query detection (nplusone). In dev it logs a warning; in the test suite it
# RAISES so an N+1 fails CI (see config/settings/test.py). Not enabled in prod.
INSTALLED_APPS = [*INSTALLED_APPS, "nplusone.ext.django"]  # noqa: F405
MIDDLEWARE = ["nplusone.ext.django.NPlusOneMiddleware", *MIDDLEWARE]  # noqa: F405
NPLUSONE_LOGGER = logging.getLogger("nplusone")
NPLUSONE_LOG_LEVEL = logging.WARN
NPLUSONE_RAISE = False
