import logging
import os

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        # Production guard: the Claude service account password must be present
        # in the environment in production. In dev/test (DEBUG=True) we only
        # warn, so the template boots with zero config.
        password = os.environ.get("CLAUDE_ADMIN_PASSWORD")
        if not password:
            message = (
                "CLAUDE_ADMIN_PASSWORD is not set. The Claude admin service "
                "account cannot sign in until it is provided (see CLAUDE.md "
                "(The Claude admin account) and .env.example)."
            )
            if settings.DEBUG:
                logger.warning(message)
            else:
                logger.error(message)
                raise ImproperlyConfigured(message)
