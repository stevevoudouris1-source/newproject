"""The embedded Matterport 3D facility tour page (see ai_context/tours.md)."""

import pytest
from django.conf import settings
from django.urls import reverse

TOUR_EMBED = "https://my.matterport.com/show/?m=Z6N6h2BYaxU"


@pytest.mark.django_db
def test_tour_requires_sign_in(client):
    response = client.get(reverse("tour"))
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


@pytest.mark.django_db
def test_signed_in_member_sees_embedded_tour(client, member_user):
    client.force_login(member_user)
    response = client.get(reverse("tour"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "<iframe" in html
    assert f'src="{TOUR_EMBED}"' in html
    # Fullscreen is what makes a walkthrough usable.
    assert "allowfullscreen" in html
    # Fallback for anyone whose browser/network blocks the embed.
    assert "Open in a new tab" in html


@pytest.mark.django_db
def test_nav_links_to_tour(client, member_user):
    client.force_login(member_user)
    html = client.get("/").content.decode()
    assert f'href="{reverse("tour")}"' in html


def test_csp_allows_only_matterport_frames():
    directives = settings.CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]
    assert directives["frame-src"] == ["https://my.matterport.com"]
    # The app itself still may not be framed by anyone.
    assert directives["frame-ancestors"] == ["'none'"]
