"""Phase 2 guardrails: rate limiting, CSP, and the service-account password floor."""

import re
from io import StringIO
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings

from apps.common import ip_allowlist


@override_settings(RATELIMIT_ENABLE=True)
@pytest.mark.django_db
def test_service_login_is_rate_limited(client):
    """The 6th login POST within a minute from one IP is blocked (403)."""
    cache.clear()  # reset the ratelimit counter
    statuses = []
    # Freeze the clock django-ratelimit reads so all six POSTs land in the same
    # fixed-window bucket. Otherwise crossing a window boundary mid-test (likely
    # under load / pytest-xdist) resets the counter and the 6th request is
    # wrongly allowed — the source of this test's historical flakiness.
    # See django_ratelimit.core._get_window.
    with mock.patch("django_ratelimit.core.time") as mock_time:
        mock_time.time.return_value = 1_700_000_000
        for _ in range(6):
            resp = client.post(
                "/accounts/login/?service=true",
                {"username": "claude@turn5.local", "password": "wrong-on-purpose"},
            )
            statuses.append(resp.status_code)
    # First 5 allowed (invalid creds re-render the form, 200); 6th is blocked.
    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[-1] == 403


@pytest.mark.django_db
def test_csp_report_only_header_present(client):
    resp = client.get("/accounts/login/")
    header = resp.headers.get("Content-Security-Policy-Report-Only", "")
    assert "default-src 'self'" in header
    assert "frame-ancestors 'none'" in header
    assert "object-src 'none'" in header


@pytest.mark.django_db
def test_rotate_claude_password_is_strong(claude_user):
    out = StringIO()
    call_command("rotate_claude_password", stdout=out)
    match = re.search(r"CLAUDE_ADMIN_PASSWORD=(\S+)", out.getvalue())
    assert match, out.getvalue()
    password = match.group(1)
    assert len(password) >= 24
    claude_user.refresh_from_db()
    assert claude_user.check_password(password)


@pytest.mark.django_db
def test_ip_allowlist_allows_all_by_default(client):
    """The committed allowed_ips.txt contains '*' -> everything is allowed."""
    ip_allowlist._CACHE["mtime"] = None  # force a re-read of the real file
    assert client.get("/up/", REMOTE_ADDR="198.51.100.7").status_code == 200


@pytest.mark.django_db
def test_ip_allowlist_restricts_to_listed_ranges(client, tmp_path, settings, member_user):
    allowfile = tmp_path / "allowed_ips.txt"
    allowfile.write_text("10.0.0.0/8\n203.0.113.5\n")
    settings.IP_ALLOWLIST_FILE = str(allowfile)
    ip_allowlist._CACHE["mtime"] = None  # bust the per-process cache

    client.force_login(member_user)
    # 127.0.0.1 is not listed -> blocked before reaching the view.
    assert client.get("/", REMOTE_ADDR="127.0.0.1").status_code == 403
    # The health check is always exempt.
    assert client.get("/up/", REMOTE_ADDR="127.0.0.1").status_code == 200
    # Addresses inside an allowed range / exact IP pass through to the view.
    assert client.get("/", REMOTE_ADDR="10.1.2.3").status_code == 200
    assert client.get("/", REMOTE_ADDR="203.0.113.5").status_code == 200

    ip_allowlist._CACHE["mtime"] = None  # leave cache clean for other tests


@pytest.mark.django_db
def test_ip_allowlist_trusts_forwarded_for_when_enabled(client, tmp_path, settings, member_user):
    allowfile = tmp_path / "allowed_ips.txt"
    allowfile.write_text("10.0.0.0/8\n")
    settings.IP_ALLOWLIST_FILE = str(allowfile)
    settings.IP_ALLOWLIST_TRUST_FORWARDED_FOR = True
    ip_allowlist._CACHE["mtime"] = None

    client.force_login(member_user)
    # Proxy address is disallowed, but the real client (X-Forwarded-For) is in range.
    resp = client.get("/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="10.9.9.9, 192.0.2.1")
    assert resp.status_code == 200

    ip_allowlist._CACHE["mtime"] = None
