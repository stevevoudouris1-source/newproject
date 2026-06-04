"""Guardrails for template hygiene.

Django's `{# ... #}` comment syntax is SINGLE-LINE only: a `{#` whose matching
`#}` is on a later line is NOT stripped and leaks into the rendered HTML as
visible text. Multi-line comments must use `{% comment %}...{% endcomment %}`.
This has bitten the login, flash, and base templates repeatedly, so we fail the
build if any template reintroduces it.
"""

from pathlib import Path

from django.conf import settings

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"


def _offending_lines(text: str) -> list[int]:
    """Line numbers where a `{#` has no closing `#}` on the same line."""
    bad = []
    for i, line in enumerate(text.splitlines(), start=1):
        start = line.find("{#")
        if start != -1 and "#}" not in line[start:]:
            bad.append(i)
    return bad


def test_no_multiline_django_comments_in_templates():
    offenders = {}
    for path in TEMPLATES_DIR.rglob("*.html"):
        lines = _offending_lines(path.read_text(encoding="utf-8"))
        if lines:
            offenders[str(path.relative_to(TEMPLATES_DIR))] = lines
    assert not offenders, (
        "Multi-line `{# #}` comments leak into rendered HTML — use "
        f"`{{% comment %}}...{{% endcomment %}}` instead. Offenders: {offenders}"
    )
