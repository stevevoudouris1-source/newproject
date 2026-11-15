"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import RateLimitedOIDCCallbackView, health_check

urlpatterns = [
    # Microsoft Entra OIDC (authenticate / callback / logout). Registered even
    # when OIDC is unconfigured; the views simply redirect/fail cleanly until
    # the tenant is set up. See .claude/skills/register-entra-app.md.
    # The callback is rate-limited; this explicit route (same name) shadows the
    # one from the include below.
    path(
        "oidc/callback/",
        RateLimitedOIDCCallbackView.as_view(),
        name="oidc_authentication_callback",
    ),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("admin/", admin.site.urls),
    # Liveness probe used by the platform / health checks. No auth.
    path("up/", health_check, name="health_check"),
    path("", include("apps.tours.urls")),
    path("", include("apps.accounts.urls")),
]
