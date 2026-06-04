"""`python manage.py rotate_claude_password`

Generates a fresh 32-char random password for the Claude admin service account,
sets it, and prints it ONCE. Rotate roughly every 90 days (see CLAUDE.md).
"""

import secrets
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

# The Claude service-account password is machine-generated and never typed by a
# human, so we generate well above the 24-char strength floor.
_MIN_LENGTH = 24
_ALPHABET = string.ascii_letters + string.digits
_LENGTH = 32
assert _LENGTH >= _MIN_LENGTH


class Command(BaseCommand):
    help = "Rotate the Claude admin service account password and print it once."

    def handle(self, *args, **options):
        User = get_user_model()
        email = settings.CLAUDE_ADMIN_EMAIL
        try:
            user = User.objects.get(username=email, is_claude_service=True)
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"No Claude service account found for {email!r}. Run `manage.py migrate` first."
                )
            )
            return

        password = "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))
        user.set_password(password)
        user.save(update_fields=["password"])

        self.stdout.write(
            self.style.SUCCESS("Rotated the Claude admin password. Shown ONCE -- store it now:")
        )
        self.stdout.write("")
        self.stdout.write(f"    CLAUDE_ADMIN_PASSWORD={password}")
        self.stdout.write("")
        self.stdout.write(
            "Paste it into .env (local) or the platform secret store / Azure Key "
            "Vault (production). It is NOT saved anywhere else."
        )
