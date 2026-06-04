"""Provision the Claude admin service account.

Idempotent: re-running updates the existing row. The password is read from the
environment (CLAUDE_ADMIN_PASSWORD) and stored only as a hash. When no password
is available (dev/test/first-run) the account is created with an UNUSABLE
password — it exists but cannot sign in until `manage.py rotate_claude_password`
(or a real password in .env) is provided. The production guard in
AccountsConfig.ready() prevents booting prod without the password set.
"""

import os

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


def provision_claude_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    email = os.environ.get(
        "CLAUDE_ADMIN_EMAIL",
        getattr(settings, "CLAUDE_ADMIN_EMAIL", "claude@turn5.local"),
    )
    raw_password = os.environ.get("CLAUDE_ADMIN_PASSWORD")
    user, _ = User.objects.update_or_create(
        username=email,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": False,
            "is_active": True,
            "role": "admin",
            "is_claude_service": True,
        },
    )
    # make_password(None) returns an unusable password hash.
    user.password = make_password(raw_password) if raw_password else make_password(None)
    user.save(update_fields=["password"])


def deprovision_claude_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    email = os.environ.get(
        "CLAUDE_ADMIN_EMAIL",
        getattr(settings, "CLAUDE_ADMIN_EMAIL", "claude@turn5.local"),
    )
    User.objects.filter(username=email, is_claude_service=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(provision_claude_admin, deprovision_claude_admin),
    ]
