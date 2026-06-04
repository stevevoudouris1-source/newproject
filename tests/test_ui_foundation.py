"""Foundation UI polish: self-hosted Inter font + vendored inline icon system.

These guard the *default* look of the template: a modern self-hosted typeface
(no CDN, offline-friendly like the vendored HTMX/Alpine) and Lucide SVG icons
rendered inline (no client JS, no emoji).
"""

import pytest
from django.template.loader import render_to_string


@pytest.mark.django_db
def test_base_preloads_self_hosted_inter(client, member_user):
    client.force_login(member_user)
    html = client.get("/").content.decode()
    # The primary font is preloaded so headings/body don't flash a fallback.
    assert 'rel="preload"' in html
    assert 'as="font"' in html
    # And it is the self-hosted Inter weight, not a Google Fonts CDN URL.
    assert "Inter-" in html
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html


@pytest.mark.django_db
def test_home_renders_inline_icons(client, member_user):
    client.force_login(member_user)
    html = client.get("/").content.decode()
    # Feature cards use vendored inline SVG icons (decorative -> aria-hidden).
    assert "<svg" in html
    assert 'aria-hidden="true"' in html


def test_icon_component_renders_named_icon():
    out = render_to_string("components/icon.html", {"name": "shield-check", "class": "h-6 w-6"})
    assert "<svg" in out
    assert "h-6 w-6" in out
    # The shield-check glyph's path data proves the right icon was selected.
    assert "M20 13c0 5" in out


def test_icon_component_supports_accessible_label():
    decorative = render_to_string("components/icon.html", {"name": "zap"})
    assert 'aria-hidden="true"' in decorative

    labelled = render_to_string("components/icon.html", {"name": "zap", "label": "Fast"})
    assert 'role="img"' in labelled
    assert 'aria-label="Fast"' in labelled
    assert "aria-hidden" not in labelled
