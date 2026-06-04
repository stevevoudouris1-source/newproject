from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

from apps.accounts.forms import UserForm
from apps.accounts.models import User
from apps.accounts.permissions import (
    MANAGE_USERS,
    VIEW_USERS,
    authorize,
    can,
)
from apps.common.pagination import paginate


def health_check(request):
    """Liveness probe for the platform / load balancer. No authentication."""
    return HttpResponse("OK", content_type="text/plain", status=200)


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class RateLimitedLoginView(LoginView):
    """Login view with brute-force protection on the (service-account) password
    form: at most 5 POSTs/minute/IP, then HTTP 403 (django-ratelimit).

    The password form is the default sign-in path. The Microsoft Entra (SSO)
    button is only offered once OIDC is actually configured (``OIDC_ENABLED``)."""

    template_name = "accounts/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oidc_enabled"] = settings.OIDC_ENABLED
        return context


@method_decorator(ratelimit(key="ip", rate="5/m", method="GET", block=True), name="get")
class RateLimitedOIDCCallbackView(OIDCAuthenticationCallbackView):
    """The Entra OIDC return URL, rate-limited to 5 hits/minute/IP."""


@login_required
def index(request):
    """Landing page: greets the user and orients them in the framework. Every
    view defaults to @login_required."""
    who = request.user.email or request.user.username
    return render(request, "index.html", {"who": who})


@login_required
def profile(request):
    can_change_password = settings.PASSWORD_LOGIN_ENABLED and request.user.has_usable_password()
    return render(request, "accounts/profile.html", {"can_change_password": can_change_password})


@login_required
def change_password(request):
    """Self-service password change for the signed-in user.

    Only meaningful while standalone password login is enabled and the user
    actually has a password (SSO-only accounts don't)."""
    if not (settings.PASSWORD_LOGIN_ENABLED and request.user.has_usable_password()):
        messages.error(request, "Password sign-in isn't enabled for your account.")
        return redirect("profile")
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # don't log the user out
        messages.success(request, "Your password has been updated.")
        return redirect("profile")
    return render(request, "accounts/change_password.html", {"form": form})


# ---------------------------------------------------------------------------
# User management
#
# Read (list/detail) is gated on VIEW_USERS; mutations (create/edit) on
# MANAGE_USERS. Admins pass both implicitly. The form grants the view permission
# alongside manage, so anyone who can manage can also view. Row access always
# goes through User.objects.for_user(request.user), never .all().
# ---------------------------------------------------------------------------


@login_required
def user_list(request):
    authorize(request.user, VIEW_USERS)
    users = User.objects.for_user(request.user).order_by("username")
    page = paginate(users, request)
    return render(
        request,
        "accounts/users/list.html",
        {"page": page, "can_manage": can(request.user, MANAGE_USERS)},
    )


@login_required
def user_detail(request, pk):
    authorize(request.user, VIEW_USERS)
    target = get_object_or_404(User.objects.for_user(request.user), pk=pk)
    return render(
        request,
        "accounts/users/detail.html",
        {
            "target": target,
            "grants": target.permissions.all().order_by("name"),
            "can_manage": can(request.user, MANAGE_USERS),
        },
    )


@login_required
def user_create(request):
    authorize(request.user, MANAGE_USERS)
    form = UserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        target = form.save()
        messages.success(request, f"Created user {target.username}.")
        return redirect("user_detail", pk=target.pk)
    return render(
        request,
        "accounts/users/form.html",
        {"form": form, "mode": "create"},
    )


@login_required
def user_edit(request, pk):
    authorize(request.user, MANAGE_USERS)
    target = get_object_or_404(User.objects.for_user(request.user), pk=pk)
    # The Claude service account is provisioned from .env and managed by the
    # admin shell; it must not be altered (or locked out) through this UI.
    if target.is_claude_service:
        messages.error(request, "The Claude service account can't be edited here.")
        return redirect("user_detail", pk=target.pk)
    form = UserForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated user {target.username}.")
        return redirect("user_detail", pk=target.pk)
    return render(
        request,
        "accounts/users/form.html",
        {"form": form, "mode": "edit", "target": target},
    )
