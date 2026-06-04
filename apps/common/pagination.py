"""Pagination helpers — every list view must paginate (CLAUDE.md → Performance).

Wraps Django's Paginator the way the Rails template wraps Pagy, and enforces a
hard cap on user-supplied page sizes via `safe_limit()`.
"""

from __future__ import annotations

from django.core.paginator import Page, Paginator

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def safe_limit(requested, *, default: int = DEFAULT_PAGE_SIZE, maximum: int = MAX_PAGE_SIZE) -> int:
    """Clamp a user-supplied page size to [1, maximum]; fall back to default."""
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, maximum))


def paginate(queryset, request, *, default: int = DEFAULT_PAGE_SIZE) -> Page:
    """Return a Django Page for `queryset`, honouring ?page and a capped ?limit."""
    per_page = safe_limit(request.GET.get("limit"), default=default)
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))
