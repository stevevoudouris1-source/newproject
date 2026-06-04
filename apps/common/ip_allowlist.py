"""Network allowlist — restrict the app to approved client IPs.

Driven by a plain-text file (default: ``allowed_ips.txt`` at the repo root) that
non-technical users can edit by hand. The default file allows all traffic; a
Turn 5 team can lock the app down to their office / VPN / intranet by listing
IPs or CIDR ranges. Changes are picked up automatically (the file is re-read when
its modification time changes — no redeploy).

The ``/up/`` health check is always allowed so load balancers can probe it.

Behind a proxy/load balancer, set ``IP_ALLOWLIST_TRUST_FORWARDED_FOR=true`` so
the real client IP (the first entry of ``X-Forwarded-For``) is checked rather
than the proxy's address. Only enable that when a trusted proxy sets the header.
"""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path

from django.conf import settings
from django.http import HttpResponseForbidden

# Per-process cache, keyed on the file's mtime so edits are picked up live.
_CACHE: dict = {"mtime": None, "allow_all": True, "networks": []}


def _parse(path: str) -> tuple[bool, list]:
    """Return (allow_all, networks). Missing/empty/comment-only file => allow all."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return True, []  # no file -> permissive default

    networks = []
    allow_all = False
    has_entry = False
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line == "*":
            allow_all = True
            continue
        has_entry = True
        try:
            networks.append(ipaddress.ip_network(line, strict=False))
        except ValueError:
            # Ignore typos rather than taking the whole app down over one bad line.
            continue
    if not has_entry and not allow_all:
        allow_all = True  # only comments/blanks -> allow all
    return allow_all, networks


def _load(path: str) -> tuple[bool, list]:
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if _CACHE["mtime"] != mtime:
        allow_all, networks = _parse(path)
        _CACHE.update(mtime=mtime, allow_all=allow_all, networks=networks)
    return _CACHE["allow_all"], _CACHE["networks"]


def _client_ip(request) -> str:
    if getattr(settings, "IP_ALLOWLIST_TRUST_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class IPAllowlistMiddleware:
    """Block requests from IPs not in ``allowed_ips.txt`` (allow-all by default)."""

    EXEMPT_PREFIXES = ("/up/",)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = getattr(settings, "IP_ALLOWLIST_FILE", "")
        allow_all, networks = _load(path) if path else (True, [])

        if allow_all or request.path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)

        try:
            addr = ipaddress.ip_address(_client_ip(request))
        except ValueError:
            addr = None

        if addr is not None and any(addr in net for net in networks):
            return self.get_response(request)

        return HttpResponseForbidden("Access to this app is restricted to approved networks.")
